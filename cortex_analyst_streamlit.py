from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import snowflake.connector
import streamlit as st

import os
from dotenv import load_dotenv

from conn_config import config_dict as cfg


HOST = cfg["host"]
DATABASE = cfg["database"]
SCHEMA = cfg["schema"]
STAGE = cfg["stage"]
FILE = cfg["file"]
PORT = cfg["port"]
WAREHOUSE = cfg["warehouse"]
ROLE = cfg["role"]

#loading the user authentication credentials from .env file
load_dotenv()

# Connecting to Snowflake
if 'CONN' not in st.session_state or st.session_state.CONN is None:
    st.session_state.CONN = snowflake.connector.connect(
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        
        host=HOST,
        port=PORT,
        warehouse=WAREHOUSE,
        role=ROLE,
    )


def send_message_to_assistant(prompt: str) -> Dict[str, Any]:
    """Calls the REST API and returns the response."""

    request_body = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
        "semantic_model_file": f"@{DATABASE}.{SCHEMA}.{STAGE}/{FILE}",
    }

    resp = requests.post(
        url=f"https://{HOST}/api/v2/cortex/analyst/message",
        json=request_body,
        headers={
            "Authorization": f'Snowflake Token="{st.session_state.CONN.rest.token}"',
            "Content-Type": "application/json",
        },
    )

    request_id = resp.headers.get("X-Snowflake-Request-Id")
    
    if resp.status_code < 400:
        return {**resp.json(), 
                "request_id": request_id}  # type: ignore[arg-type]
    
    else:
        raise Exception(
            f"Failed request (id: {request_id}) with status {resp.status_code}: {resp.text}"
        )


def process_message(prompt: str) -> None:
    """Processes a message and adds the response to the chat."""
    
    st.session_state.messages.append(
        {"role": "user", 
         "content": [{"type": "text", "text": prompt}]}
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("The assistant is working on your question..."):
            response = send_message_to_assistant(prompt=prompt)
            request_id = response["request_id"]
            content = response["message"]["content"]
            display_content(content=content, request_id=request_id)  # type: ignore[arg-type]
    
    st.session_state.messages.append(
        {"role": "assistant", 
         "content": content, 
         "request_id": request_id}
    )
    print(st.session_state.messages)


def display_content(
    content: List[Dict[str, str]],
    request_id: Optional[str] = None,
    message_index: Optional[int] = None,
) -> None:
    
    """Displays a content item for a message."""

    message_index = message_index or len(st.session_state.messages)

    if request_id:
        with st.expander("Request ID", expanded=False):
            st.markdown(request_id)

    for item in content:
        
        if item["type"] == "text":
            st.markdown(item["text"])
        
        elif item["type"] == "suggestions":
            with st.expander("Suggestions", expanded=True):
                for suggestion_index, suggestion in enumerate(item["suggestions"]):
                    if st.button(suggestion, key=f"{message_index}_{suggestion_index}"):
                        st.session_state.active_suggestion = suggestion
        
        elif item["type"] == "sql":
            with st.expander("Generated SQL Query", expanded=False):
                st.code(item["statement"], language="sql")
            
            with st.expander("Query Results", expanded=True):
                with st.spinner("Running generated SQL Query..."):
                    df = pd.read_sql(item["statement"], st.session_state.CONN)
                    
                    if len(df.index) > 1:
                        data_tab, line_tab, bar_tab, area_chart_tab = st.tabs(
                            ["Data", "Line Chart", "Bar Chart", "Area Chart"]
                        )
                        data_tab.dataframe(df)
                        if len(df.columns) > 1:
                            df = df.set_index(df.columns[0])
                        
                        with line_tab:
                            st.line_chart(df)
                        
                        with bar_tab:
                            st.bar_chart(df)

                        with area_chart_tab:
                            st.area_chart(df)
                    
                    else:
                        st.dataframe(df)

st.set_page_config(
    page_title="AI Supply chain analyst",
    page_icon="imgs/avatar_streamly.png",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": "https://github.com/AdieLaine/Streamly",
        "Report a bug": "https://github.com/AdieLaine/Streamly",
        "About": """
            ## Streamly Streamlit Assistant
            ### Powered using GPT-4o-mini

            **GitHub**: https://github.com/AdieLaine/

            The AI Assistant named, Streamly, aims to provide the latest updates from Streamlit,
            generate code snippets for Streamlit widgets,
            and answer questions about Streamlit's latest features, issues, and more.
            Streamly has been trained on the latest Streamlit updates and documentation.
        """
    }
)

st.title(cfg["assistant_name"])
st.markdown(f"Semantic Model being used: `{FILE}`")

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.suggestions = []
    st.session_state.active_suggestion = None

for message_index, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        display_content(
            content=message["content"],
            request_id=message.get("request_id"),
            message_index=message_index,
        )

if user_input := st.chat_input("Please enter your question."):
    process_message(prompt=user_input)

if st.session_state.active_suggestion:
    process_message(prompt=st.session_state.active_suggestion)
    st.session_state.active_suggestion = None