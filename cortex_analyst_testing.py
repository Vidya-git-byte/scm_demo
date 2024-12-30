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


NUMBER_OF_MESSAGES_TO_DISPLAY = 5

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


def initialize_session_state():
    """Initialize session state variables."""
    if "history" not in st.session_state:
        st.session_state.history = []
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []


initialize_session_state()

if not st.session_state.history:
    initial_bot_message = "Hello! How can I assist you today?"
    st.session_state.history.append({"role": "assistant", "content": initial_bot_message})
    # st.session_state.conversation_history = initialize_conversation()

# st.sidebar.markdown("---")

# # Sidebar for Mode Selection
# mode = st.sidebar.radio("Select Mode:", options=["About", "Show chat history"], index=1)

# st.sidebar.markdown("---")

show_basic_info = st.sidebar.checkbox("About", value=True)
if show_basic_info:
    st.sidebar.markdown("""
    This is an AI analyst built on top of Snowflake Cortex AI
    """)


show_chat_history = st.sidebar.checkbox("Show chat history.", value=False)
if show_chat_history:
    st.sidebar.markdown("""
    ### Chat History
    """)
    # Display chat history
    for message in st.session_state.messages[-NUMBER_OF_MESSAGES_TO_DISPLAY:]:
        role = message["role"]
        avatar_image = "imgs/avatar_streamly.png" if role == "assistant" else "imgs/stuser.png" if role == "user" else None
        with st.chat_message(role):
            st.sidebar.write(f'**{message["role"]}** :')
            st.sidebar.write(message["content"][0]["text"])


dark_theme = """
<style>
    /* Main background */
    .stApp {
        background-color: #202123;
        color: #FFFFFF;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background-color: #202123;
    }
    
    /* Chat containers */
    .chat-container {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    
    /* User message style */
    .user-message {
        background-color: #343541;
    }
    
    /* Assistant message style */
    .assistant-message {
        background-color: #444654;
    }
    
    /* Input text area */
    .stTextInput>div>div>input {
        background-color: #40414F;
        color: #FFFFFF;
        border-color: #40414F;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #40414F;
        color: #FFFFFF;
        border: none;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #202123;
    }
    ::-webkit-scrollbar-thumb {
        background: #40414F;
        border-radius: 5px;
    }
</style>
"""

st.markdown(dark_theme, unsafe_allow_html=True)

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