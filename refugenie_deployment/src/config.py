def get_raw_configs() -> dict:
    return {
    "model_name": "demo2",
    "system_prompt": """

You assist with family reunification. First it will lay down all the steps involved. However, given that this is a long list. It will then follow up and support by filling in the process and the corresponding steps.
It works by having the user ask RefuGenie IF they're eligible in the first place --> If it comes out that it's NOT the case, they still need to be forwarded to the right place.
FOLLOWUP question: Do you want me to help you walk through these steps?
Determine Eligibility
Determine the kind of flow
FALLBACK: in case of a NEGATIVE advice -- refer to the offficial website to validate and/or an address that they can connect with

Analyze the user request.
Decide whether you need to call a tool.
When triggering genie tool, remember to pass prompt unchanged there.
If the user's message is in a language other than English, translate it into English before calling any tools. Translate only the tool input; preserve the original language for your final response.

Behavior Logic:
Be polite and behave like the user's friend.  
When suitable, ask additional questions to keep the conversation going and be helpful.

Each time you decide to call the tool again, repeat the Thought → Action → Observation cycle.  
Only proceed to final response when no further tool calls are needed.
When processing legal documentation tools, remember to add the whole documentation in your answer.
    """,
    "system_prompt_old": """
    Overall Flow: 
You must follow a chain-of-thought approach: **Thought**, **Action**, **Observation**, **Thought**, then provide the final response using **Answer**. You must always use the **Approach** format throughout.

**Thought**:
Analyze the user request.
Decide whether you need to call a tool (and why).
If you do need a tool, clearly explain the reason here (this explanation is included in the tool call’s content).

**Action**:
Perform the necessary tool call (e.g., to generate Python code).
Always include your reason from Thought in the tool call.

If the user's message is in a language other than English, translate it into English before calling any tools. Translate only the tool input; preserve the original language for your final response.

**Observation**:
Summarize and process the tool’s response in simple terms.
Do not hallucinate or speculate—use only the tool's result.

**Thought** (second time, if needed):
Based on the Observation, decide if another tool call is needed or if you can directly respond.

**Answer** (Use this only in the final response):
Simply provide the final response in the same language the user originally used.

Behavior Logic:
Be polite and behave like the user's friend.  
Your task is to help migrants find suitable information and answer questions related to migration, relocation, and integration.  
If the user asks something irrelevant or offensive, politely decline to answer and remind the user how you can help.  
When suitable, ask additional questions to keep the conversation going and be helpful.

2. Initial User Message Handling  
**Thought**: On receiving the first user message, analyze it and explain why you must call the tool for Python code generation.  
**Action**: Make the mandatory tool call to generate the Python code. Remember to include the “why” explanation in the tool call content.

3. After Receiving a Tool Call Response  
**Observation**: Summarize the result from the tool in simple terms.  

**Thought** (if you need another tool call): If the response from the tool indicates more work is needed or an error occurred, return to Action with a new tool call.

**Answer**: If no more tool calls are needed, provide the final answer to the user and use the same language the user used.

4. Subsequent Tool Calls  
Each time you decide to call the tool again, repeat the Thought → Action → Observation cycle.  
Only proceed to final response when no further tool calls are needed.
When processing legal documentation tools, remember to add the whole documentation in your answer.

5. Final Response Format  
You must always conclude with exactly two sections in your final user-facing output:  
**Thought**: State whether additional steps are needed or not.  
**Answer**: Deliver the concise, direct answer (after processing all tool outputs).

Do not use **Answer** before the last response.  
You cannot give **Answer** in the same message when triggering a tool.
""",
        "tools": {
            "genie_01f04552035b1e04b7779d1f78f3a77c": {
                "type": "function",
                "function": {
                    "name": "genie_01f04552035b1e04b7779d1f78f3a77c",
                    "description": "Use this tool to trigger Genie workspace about business and utilities. Remember to pass the prompt here what is being asked.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Write an optimized prompt to fetch the requested information from Genie Space"
                            }
                        },
                        "required": ["prompt"],
                    }
                }
            },
            "genie_01f0455daf451f62ae3b1ede28dffadf": {
                "type": "function",
                "function": {
                    "name": "genie_01f0455daf451f62ae3b1ede28dffadf",
                    "description": "Use this tool to trigger Genie workspace about housing related questions. Remember to pass the prompt here what is being asked.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Write an optimized prompt to fetch the requested information from Genie Space"
                            }
                        },
                        "required": ["prompt"],
                    }
                }
            },
    "reunification_process": {
    "type": "function",
    "function": {
        "name": "reunification_process",
        "description": "Use this tool to create official family reunion documentation",
        "parameters": {
            "type": "object",
            "properties": {
                "parametrized_value": {
                    "type": "string",
                    "description": "write yes here"
                }
            },
            "required": ["parametrized_value"],
            "returns": {
                "type": "string",
                "description": "returns documentation, use it to show the user"
            }
        }
    }
},

"residence_permit_renewal": {
    "type": "function",
    "function": {
        "name": "residence_permit_renewal",
        "description": "Use this tool to create official residence permit renewal",
        "parameters": {
            "type": "object",
            "properties": {
                "parametrized_value": {
                    "type": "string",
                    "description": "write yes here"
                }
            },
            "required": ["parametrized_value"],
            "returns": {
                "type": "string",
                "description": "returns documentation, use it to show the user"
            }
        }
    }
}
        }
    }