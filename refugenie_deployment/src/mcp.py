import asyncio
from llama_index.llms.databricks import Databricks
from databricks.sdk import WorkspaceClient
import mlflow
from dotenv import load_dotenv
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
import os
from llama_index.core.agent.workflow import ReActAgent

class NimbleResearchAgent():
    def __init__(self, nimble_api_key, databricks_model="demo2"):
        self.nimble_api_key = nimble_api_key
        self.databricks_model = databricks_model
        self.agent = None
        self.tools = None
        
    async def setup(self):
        """Set up the agent with Nimble tools and Databricks LLM."""
        # Set up Nimble tools
        self.tools = await self._setup_nimble_tools()
        
        # Set up Databricks LLM
        w = WorkspaceClient()
        tmp_token = w.tokens.create(comment="for model serving", lifetime_seconds=1200).token_value
        
        llm = Databricks(
            model=self.databricks_model,
            api_key=tmp_token,
            api_base=f"{w.config.host}/serving-endpoints/"
        )
        
        # Create the agent
        self.agent = ReActAgent(
            tools=self.tools,
            llm=llm,
            system_prompt="""You are a helpful research assistant with access to web scraping and data collection tools. 
            Always explain your answer in the final output. Tell the user which tools you used and how you found the information.""",
        )
        
        return self
        
    async def _setup_nimble_tools(self):
        """Set up and return the Nimble tools."""
        mcp_client = BasicMCPClient(
            "https://mcp.nimbleway.com/sse",
            headers={"Authorization": f"Bearer {self.nimble_api_key}"}
        )
        
        mcp_tool_spec = McpToolSpec(
            client=mcp_client,
            # Optional: filter to specific tools
            # allowed_tools=["nimble_web_search", "nimble_google_maps_search"]
        )
        
        tools = await mcp_tool_spec.to_tool_list_async()
        
        print(f"Loaded {len(tools)} Nimble tools:")
        for tool in tools:
            print(f"- {tool.metadata.name}: {tool.metadata.description}")
        
        return tools
    
    async def run_query(self, query):
        """
        Run a query through the agent.
        
        Args:
            query: The query string to process
            
        Returns:
            The agent's response
        """
        if not self.agent:
            raise ValueError("Agent not initialized. Call setup() first.")
        
        return await self.agent.run(query)