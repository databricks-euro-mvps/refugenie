import dash
from dash import html, Input, Output, State, dcc
import dash_bootstrap_components as dbc
from databricks.sdk import WorkspaceClient
from databricks.sdk.credentials_provider import ModelServingUserCredentials
import json
import time
from openai import OpenAI
import yaml
import os 
import flask 
import re


def extract_assistant_and_tool_messages(chat_completion):
    messages = chat_completion.messages
    assistant_and_tool_messages = [message for message in messages if message['role'] in ['assistant', 'tool']]
    return assistant_and_tool_messages

class DatabricksChatbot:
    def __init__(self, app, endpoint_name, agent_name, height='600px'):
        self.app = app
        self.endpoint_name = endpoint_name
        self.agent = agent_name
        self.height = height

        try:
            self.w = WorkspaceClient()
        except Exception as e:
            self.w = None
        
        # self.get_authentication()
        self._create_callbacks()
        self._add_custom_css()

    def _create_layout(self, user_name):
        user_name_cleaned = user_name.split('@')[0].capitalize()
        default_message = f"Hello {user_name_cleaned}! I'm here to help you with questions about your new country. Remember, I can help with your mother language"

        return html.Div([
            html.Div([
                # Logo on the left
                html.Div([
                    html.Img(src='https://futurumgroup.com/wp-content/uploads/2025/04/dais25-promo-556x313-2x.png', style={'max-height': '90px', 'margin-top': '16px',  'margin-right': '15px'})
                ], className='d-flex align-items-center'),
                
                # Title and content on the right
                html.Div([
                    html.H2(f'RefuGenie - Navigate with hope 🧭', 
                            className='chat-title mb-3',
                            style={'color': 'white', 'text-align': 'left', 'margin': '0'})
                ], className='flex-grow-1', style={'background-color': '#BD2A26', 'padding': '10px', 'border-radius': '5px'})
            ], className='d-flex align-items-center mb-3'),

            # Added description text under header
            html.Div([
                html.P("RefuGenie helps you navigate your new country", 
                    style={'text-align': 'left', 'margin-bottom': '0', 'font-size': '16px', 'color': 'white'})
            ], style={'background-color': '#BD2A26', 'padding': '10px', 'border-radius': '5px', 'margin-bottom': '20px'}),

            dbc.Card([
                dbc.CardBody([
                    html.Div([
                        html.Div(default_message, className='chat-message assistant-message')
                    ], id='chat-history', className='chat-history'),
                ], className='d-flex flex-column chat-body')
            ], className='chat-card mb-3'),
            dbc.InputGroup([
                dbc.Input(id='user-input', placeholder='Type your message here...', type='text'),
                dbc.Button('Send', id='send-button', color='success', n_clicks=0, className='ms-2'),
                dbc.Button('Clear', id='clear-button', color='danger', n_clicks=0, className='ms-2'),
            ], className='mb-3'),
            dcc.Store(id='assistant-trigger'),
            dcc.Store(id='chat-history-store'),
            dcc.Store(id='processing-flag', data=False),
            dcc.Store(id='user-name-store', data=user_name),  # Store the user name
            html.Div(id='dummy-output', style={'display': 'none'}),
        ], className='d-flex flex-column chat-container p-3', style={'background-color': '#FF3620', 'min-height': '100vh'})

    def _create_callbacks(self):
        @self.app.callback(
            Output('chat-history-store', 'data', allow_duplicate=True),
            Output('chat-history', 'children', allow_duplicate=True),
            Output('user-input', 'value'),
            Output('assistant-trigger', 'data'),
            Output('processing-flag', 'data'),
            Input('send-button', 'n_clicks'),
            Input('user-input', 'n_submit'),
            State('user-input', 'value'),
            State('chat-history-store', 'data'),
            prevent_initial_call=True
        )
        def update_chat(send_clicks, user_submit, user_input, chat_history):  
            if not user_input:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update, False

            # Initialize chat_history
            chat_history = chat_history or []  
            chat_history.append({'role': 'user', 'content': user_input})
            chat_display = self._format_chat_display(chat_history)
            chat_display.append(self._create_typing_indicator())
            return chat_history, chat_display, '', {'trigger': True}, True

        @self.app.callback(
            Output('chat-history-store', 'data', allow_duplicate=True),
            Output('chat-history', 'children', allow_duplicate=True),
            Output('processing-flag', 'data', allow_duplicate=True),
            Input('assistant-trigger', 'data'),
            State('chat-history-store', 'data'),
            State('user-name-store', 'data'),
            prevent_initial_call=True
        )
        def process_assistant_response(trigger, chat_history, user_store):
            if not trigger or not trigger.get('trigger'):
                return dash.no_update, dash.no_update

            chat_history = chat_history or []
            if (not chat_history or not isinstance(chat_history[-1], dict)
                    or 'role' not in chat_history[-1]
                    or chat_history[-1]['role'] != 'user'):
                return dash.no_update, dash.no_update, False

            try:
                assistant_response = self._call_model_endpoint(chat_history, user_store)
                chat_history.append({
                    'role': 'assistant',
                    'content': assistant_response
                })
            except Exception as e:
                error_message = f'Error: {str(e)}'
                chat_history.append({
                    'role': 'assistant',
                    'content': error_message
                })

            chat_display = self._format_chat_display(chat_history)
            return chat_history, chat_display, False
        
        @self.app.callback(
            Output('user-input', 'disabled'),
            Output('send-button', 'disabled'),
            Input('processing-flag', 'data')
        )
        def toggle_input_disable(is_processing):
            return is_processing, is_processing

        @self.app.callback(
            Output('chat-history-store', 'data', allow_duplicate=True),
            Output('chat-history', 'children', allow_duplicate=True),
            Input('clear-button', 'n_clicks'),
            prevent_initial_call=True
        )
        def clear_chat(n_clicks):
            if n_clicks:
                return [], []
            return dash.no_update, dash.no_update

    def _call_model_endpoint(self, messages, user_name, max_tokens=750):

        function_call_messages = messages.copy()  # Copying messages to avoid modifying the original messages
        # Modify the last message's content to add user name there
        #function_call_messages[-1]['content'] = f"The current user: {user_name.split('@')[0].capitalize()}\n" + function_call_messages[-1]['content']
        
        try:
            we = WorkspaceClient(credentials_strategy=ModelServingUserCredentials())
            client = we.serving_endpoints.get_open_ai_client()
            results = client.chat.completions.create(model=self.agent, messages=function_call_messages)
            
            messages = extract_assistant_and_tool_messages(results)

            ### Clean answer results only
            raw_result = results.messages[-1]['content']
            pattern = r'\*\*Answer\*\*:([\s\S]*)$'
            match = re.search(pattern, raw_result, re.MULTILINE)

            if match:
                cleaned_result = match.group(1).strip()  # group(1) refers to the captured group (the part in parentheses)
                return cleaned_result
            else:
                return raw_result 
            
        except Exception as e:
            raise

    def _format_chat_display(self, chat_history):
        formatted_messages = []
        
        for msg in chat_history:
            if isinstance(msg, dict) and 'role' in msg and msg['role'] != 'system':
                if msg['role'] == 'assistant':
                    # Use Dash's Markdown component for assistant messages
                    message_content = dcc.Markdown(
                        msg['content'],
                        className=f"chat-message {msg['role']}-message"
                    )
                else:
                    # For user messages, keep as plain text
                    message_content = html.Div(
                        msg['content'],
                        className=f"chat-message {msg['role']}-message"
                    )
                
                formatted_messages.append(
                    html.Div(
                        message_content,
                        className=f"message-container {msg['role']}-container"
                    )
                )
        
        return formatted_messages

    def _create_typing_indicator(self):
        return html.Div([
            html.Div(className='chat-message assistant-message typing-message',
                     children=[
                         html.Div(className='typing-dot'),
                         html.Div(className='typing-dot'),
                         html.Div(className='typing-dot')
                     ])
        ], className='message-container assistant-container')

    def _add_custom_css(self):
        custom_css = '''
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');
        body {
            font-family: 'DM Sans', sans-serif;
            background-color: #F9F7F4; /* Oat Light */
        }
        .chat-container {
            max-width: 800px;
            margin: 0 auto;
            background-color: #FFFFFF;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .chat-title {
            font-size: 24px;
            font-weight: 700;
            color: #1B3139; /* Navy 800 */
            text-align: center;
        }
        .chat-card {
            border: none;
            background-color: #EEEDE9; /* Oat Medium */
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .chat-body {
            flex-grow: 1;
            overflow: hidden;
            display: flex;
            flex-direction: column;
        }
        .chat-history {
            flex-grow: 1;
            overflow-y: auto;
            padding: 15px;
        }
        .message-container {
            display: flex;
            margin-bottom: 15px;
        }
        .user-container {
            justify-content: flex-end;
        }
        .chat-message {
            max-width: 80%;
            padding: 10px 15px;
            border-radius: 20px;
            font-size: 16px;
            line-height: 1.4;
        }
        .user-message {
            background-color: #BD2A26; /* #FF3621;  Databricks Orange 600 */
            color: white;
        }
        .assistant-message {
            background-color: #1B3139; /* Databricks Navy 800 */
            color: white;
        }
        .typing-message {
            background-color: #2D4550; /* Lighter shade of Navy 800 */
            color: #EEEDE9; /* Oat Medium */
            display: flex;
            justify-content: center;
            align-items: center;
            min-width: 60px;
        }
        .typing-dot {
            width: 8px;
            height: 8px;
            background-color: #EEEDE9; /* Oat Medium */
            border-radius: 50%;
            margin: 0 3px;
            animation: typing-animation 1.4s infinite ease-in-out;
        }
        .typing-dot:nth-child(1) { animation-delay: 0s; }
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing-animation {
            0% { transform: translateY(0px); }
            50% { transform: translateY(-5px); }
            100% { transform: translateY(0px); }
        }
        #user-input {
            border-radius: 20px;
            border: 1px solid #DCE0E2; /* Databricks Gray - Lines */
        }
        #send-button, #clear-button {
            border-radius: 20px;
            width: 100px;
        }
        #send-button {
            background-color: #00A972; /* Databricks Green 600 */
            border-color: #00A972;
        }
        #clear-button {
            background-color: #98102A; /* Databricks Maroon 600 */
            border-color: #98102A;
        }
        .input-group {
            flex-wrap: nowrap;
        }

        /* Newly added improved markdown CSS additions to enable custom CSS in chat response */
        .assistant-message h1, .assistant-message h2, .assistant-message h3 {
            margin-top: 10px;
            margin-bottom: 10px;
            color: white;
        }

        .assistant-message h1 {
            font-size: 22px;
        }

        .assistant-message h2 {
            font-size: 20px;
        }

        .assistant-message h3 {
            font-size: 18px;
        }

        .assistant-message strong {
            font-weight: bold;
        }

        .assistant-message br {
            margin-bottom: 5px;
        }

        /* Style for code blocks if needed */
        .assistant-message code {
            background-color: #3d4f57;
            padding: 2px 4px;
            border-radius: 3px;
        }

        .assistant-message pre {
            background-color: #3d4f57;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
            margin: 10px 0;
        }


        '''
        self.app.index_string = self.app.index_string.replace(
            '</head>',
            f'<style>{custom_css}</style></head>'
        )

        self.app.clientside_callback(
            """
            function(children) {
                var chatHistory = document.getElementById('chat-history');
                if(chatHistory) {
                    chatHistory.scrollTop = chatHistory.scrollHeight;
                }
                return '';
            }
            """,
            Output('dummy-output', 'children'),
            Input('chat-history', 'children'),
            prevent_initial_call=True
        )