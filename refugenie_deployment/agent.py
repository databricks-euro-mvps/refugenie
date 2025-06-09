from databricks.sdk import WorkspaceClient

import mlflow
from mlflow import tracing
from mlflow.pyfunc.model import ChatAgent
from mlflow.types.agent import (
    ChatAgentChunk,
    ChatAgentMessage,
    ChatAgentResponse,
    ChatContext
)

import json
import time
from openai import OpenAI
import requests 
from requests.exceptions import RequestException
from typing import List, Generator, Any, Optional, Dict
import os
import re 
from uuid import uuid4


from src.functions import call_chat_model, create_tool_calls_output
from src.config import get_raw_configs
from src.general_functions import get_workspace_client
from src.genie_functions import run_genie
from src.tool_functions import reunification_process, residence_permit_renewal


#### Set up agent monitoring
mlflow.openai.autolog(log_traces=True)

experiment_name = "/RefuGenie"
mlflow.set_experiment(experiment_name)

#### Get the experiment details
experiment = mlflow.get_experiment_by_name(experiment_name)
tracing.set_destination(
  tracing.destination.Databricks(experiment_id=experiment.experiment_id)
)

class RefuGenie(ChatAgent):
    def __init__(self):

        self.get_configs()  
        self.w_system = get_workspace_client('system')
        self.openai_client = self.w_system.serving_endpoints.get_open_ai_client()

    def get_configs(self):
        config_data = get_raw_configs()
        self.system_prompt = config_data['system_prompt']
        self.model_name = config_data['model_name']
        self.tools = [value for key, value in config_data['tools'].items()]
        self.function_mapping = {tool['function']['name']: globals().get(tool['function']['name']) for tool in self.tools}


    def stringify_tool_call(self, response: object) -> dict:
        try:
            # Extract message details
            value = response.choices[0].message

            # Construct payload
            payload = {
                "role": value.role,
                "content": value.content,
                "name": None,  # No name provided, use None
                "id": response.id,  # New id with 'run-' prefix
                "tool_calls": create_tool_calls_output(value),
                "tool_call_id": None,  # No tool_call_id in the input, set to None
                "attachments": None  # No attachments in the input, set to None
            } 

            return ChatAgentMessage(**payload) 
        
        except (AttributeError, IndexError) as e:
            raise ValueError(f"Invalid response format: {e}")
         
  
    def process_tool_calls(self, response: object) -> list:
        # Fetching the assistant message
        new_messages = []
        new_messages.append(self.stringify_tool_call(response))
        # Start processing tool call one by one
        tool_calls = response.choices[0].message.tool_calls

        for tool_call in tool_calls:
            try:
                # Extract function name and arguments
                function_name = tool_call.function.name
                print(function_name, "TRIGGERED")
                if function_name not in self.function_mapping:
                    raise ValueError(f"Unknown function name: {function_name}")
    
                # Parse the function arguments
                function_arguments = json.loads(tool_call.function.arguments)

                function_name = tool_call.function.name

                # This part is "hard coded" for demo purpose only - normally would be dynamic function list
                if "genie" in function_name:
                    tool_prompt = function_arguments['prompt']
                    genie_space_id = function_name.split('_')[1]
                    results = run_genie(genie_space_id = genie_space_id, prompt = tool_prompt)

                elif "reunification_process" in function_name:
                    parametrized_value = function_arguments['parametrized_value']
                    results = reunification_process(parametrized_value)
                elif "residence_permit_renewal" in function_name:
                    parametrized_value = function_arguments['parametrized_value']
                    results = residence_permit_renewal(parametrized_value)              
                else:
                    raise Exception(f"An error occurred - function not found: {function_name}")
               
                # Add validator that function_output is ALWAYS a string
                if not isinstance(results, str):
                    raise ValueError(f"Function '{function_name}' did not return a string.")

                # Create the payload
                payload = {
                    "role": "tool",
                    "content": results,  # Call the mapped function
                    "name": function_name,
                    "tool_call_id": tool_call.id,
                    "id": str(uuid4())
                }

                # Append the processed payload
                new_messages.append(ChatAgentMessage(**payload))
            except Exception as e:
                raise RuntimeError(f"Error processing tool call {tool_call.id}: {e}")
        return new_messages


    def agent_tool_calling(self, messages):

        ### Hard coded values here
        temperature = 0.3
        max_tokens= 10000
        max_node_count = 8  # Max 8 nodes just in case to avoid infinity loops
        node_count = 1

        try:
            result = call_chat_model(self.openai_client, self.model_name, messages, temperature, max_tokens, tools = self.tools)
            if result.choices[0].finish_reason == 'length':
                yield "You are running out of tokens. Please reduce the number of tokens or increase the node count."

            if result.choices[0].finish_reason == 'stop':
                yield ChatAgentMessage(**result.choices[0].message.to_dict(), id=result.id)

            # Activating the Agent
            while result.choices[0].finish_reason != 'stop' and node_count <= max_node_count:

                # Processing tool_calls
                for temp_message in self.process_tool_calls(result):
                    messages.append(temp_message)
                    yield temp_message

                # adding one full node count
                node_count += 1

                # Calling chat model again
                result = call_chat_model(self.openai_client, self.model_name, messages, temperature, max_tokens, tools = self.tools)
            
            # Processing the last agent reply on the loop and avoiding duplicated yield values on single replies.
            if node_count > 1:
                yield ChatAgentMessage(**result.choices[0].message.to_dict(), id=result.id)
        
        except Exception as e:
            print(f'Error occurred: {e}')

    def predict(self, 
                messages: List[ChatAgentMessage],
                context: Optional[ChatContext] = None,
                custom_inputs: Optional[dict[str, Any]] = None,
                ) -> ChatAgentResponse:  

        message_state = [
            ChatAgentMessage(role="system", content=self.system_prompt)
            ] + messages

        response_messages = [
            chunk.delta
            for chunk in self.predict_stream(message_state, context, custom_inputs)
        ]
        return ChatAgentResponse(messages=response_messages)

    def predict_stream(  
        self,  
        messages,  
        context=None,  
        custom_inputs=None,  
    ):  
        message_state = [
            ChatAgentMessage(role="system", content=self.system_prompt)
            ] + messages
    
        for message in self.agent_tool_calling(messages=message_state):
            yield ChatAgentChunk(delta=message)

agent = RefuGenie()
mlflow.models.set_model(agent)