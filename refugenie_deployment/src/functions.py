from pydantic import BaseModel, field_validator
from typing import List, Generator, Any, Optional, Dict
import re 
import requests
from uuid import uuid4
from mlflow.types.agent import (
    ChatAgentMessage,
    ChatAgentResponse
)

class ToolException(Exception):
    """Custom exception for tool-related errors."""
    pass

class ToolFunctionCall(BaseModel):
    name: str
    arguments: str  # ✅ Now just a string (JSON)

    def get_parsed_arguments(self) -> Dict[str, Any]:
        import json
        return json.loads(self.arguments)
    
class ToolCall(BaseModel):
    id: str
    type: str
    function: ToolFunctionCall

class ToolCallsOutput(BaseModel):
    tool_calls: List[ToolCall]

def create_tool_calls_output(results: object) -> dict:
    tool_calls = []

    for tool_call in results.tool_calls:
        function_arguments = tool_call.function.arguments
        if isinstance(function_arguments, dict):
            function_arguments = json.dumps(function_arguments)

        tool_call_model = ToolCall(
            id=tool_call.id,
            type=tool_call.type,
            function=ToolFunctionCall(
                name=tool_call.function.name,
                arguments=function_arguments 
            )
        )
        tool_calls.append(tool_call_model)

    return ToolCallsOutput(tool_calls=tool_calls).model_dump()["tool_calls"]


def prepare_messages_for_llm(messages: list[ChatAgentMessage]) -> list[dict[str, Any]]:
    """Filter out ChatAgentMessage fields that are not compatible with LLM message formats"""
    compatible_keys = ["role", "content", "name", "tool_calls", "tool_call_id"]
    return [
        {k: v for k, v in m.model_dump_compat(exclude_none=True).items() if k in compatible_keys} for m in messages
    ]


def call_chat_model(openai_client: any, model_name: str, messages: list, temperature: float = 0.3, max_tokens: int = 1000, **kwargs):
    chat_args = {
        "model": model_name,  
        "messages": prepare_messages_for_llm(messages),
        "max_tokens": max_tokens,
        "temperature": temperature,
        **kwargs, 
    }
    try:
        chat_completion = openai_client.chat.completions.create(**chat_args)
        return chat_completion  
    except Exception as e:
        error_message = f"Model endpoint calling error: {e}"
        print(error_message)
        raise RuntimeError(error_message)
