from typing import Any, Dict, List, Optional
import pandas as pd
import requests
import snowflake.connector
# import streamlit as st
from datetime import datetime
import base64

import os
from dotenv import load_dotenv

from conn_config import config_dict as cfg

from snowflake.cortex import Complete
from snowflake.snowpark import Session
import openai


# Constants:

HOST = cfg["host"]
DATABASE = cfg["database"]
SCHEMA = cfg["schema"]
STAGE = cfg["stage"]
FILE = cfg["file"]
PORT = cfg["port"]
WAREHOUSE = cfg["warehouse"]
ROLE = cfg["role"]

APP_ICON_PATH = cfg["app_icon"]
USER_ICON_PATH = cfg["user_icon"]
BOT_ICON_PATH = cfg["assistant_icon"]


#loading the user authentication credentials from .env file
load_dotenv()

OPENAI_KEY = os.environ["OpenAI_api_key"]
# Connecting to Snowflake
# if 'CONN' not in st.session_state or st.session_state.CONN is None:
#     st.session_state.CONN = snowflake.connector.connect(
#         user=os.environ["SNOWFLAKE_USER"],
#         password=os.environ["SNOWFLAKE_PASSWORD"],
#         account=os.environ["SNOWFLAKE_ACCOUNT"],
        
#         host=HOST,
#         port=PORT,
#         warehouse=WAREHOUSE,
#         role=ROLE,
#     )

connection_params = {
    "account": os.environ["SNOWFLAKE_ACCOUNT"],
    "user": os.environ["SNOWFLAKE_USER"],
    "password": os.environ["SNOWFLAKE_PASSWORD"],
}

# Create a Snowflake session
snowflake_session = Session.builder.configs(connection_params).create()

# def get_insight(prompt: str):
    
#     # api_url = f"https://{HOST}/api/v2/cortex/analyst/message"
#     api_url=f"https://{HOST}/api/v2/cortex/inference:complete"

#     payload = {
#         "messages": [
#             {
#                 "role": "user",
#                 "content": [{"type": "text", "text": prompt}]
#             }
#         ],
#         "semantic_model_file": f"@{DATABASE}.{SCHEMA}.{STAGE}/{FILE}"
#     }

#     # API headers
#     headers = {
#         "Authorization": f'Snowflake Token="{st.session_state.CONN.rest.token}"',
#         "Content-Type": "application/json"
#     }

#     # Make the API call
#     response = requests.post(api_url, json=payload, headers=headers)

#     # Handle API response
#     if response.status_code < 400:
#         response_content = response.json()
#         # Extract the LLM's response text
#         insights = response_content["message"]["content"][0]["text"]
        
#         return insights
#     else:
#         raise Exception(
#             f"Failed to generate insights with status {response.status_code}: {response.text}"
#         )
    
def get_ai_response(prompt):
     completion = Complete(
        model="llama2-70b-chat",
        prompt=prompt,
        session=snowflake_session,
    )
    
# if user_input := st.chat_input("Ask me a question."):
#         st.markdown(get_ai_response(prompt=user_input))

def get_chatgpt_response(user_prompt, model="gpt-3.5-turbo"):
    """
    Gets a response from ChatGPT for a given user prompt.
    
    Parameters:
        api_key (str): Your OpenAI API key.
        user_prompt (str): The input prompt for the ChatGPT model.
        model (str): The model to use (default is "gpt-3.5-turbo").
    
    Returns:
        str: The response from ChatGPT.
    """
    # Set the OpenAI API key
    openai.api_key = OPENAI_KEY
    
    try:
        # Make the API call to OpenAI
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for supply chain analysis."},
                {"role": "user", "content": user_prompt},
            ]
        )
        
        # Extract the content of the assistant's response
        return response['choices'][0]['message']['content'].strip()
    
    except Exception as e:
        return f"An error occurred: {e}"

def main():
     user_input = input()
     print(get_chatgpt_response(user_input))
    
if __name__ == "__main__":
     main()

