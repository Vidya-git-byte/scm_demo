from typing import Any, Dict, List, Optional
import pandas as pd
import requests
import snowflake.connector
import streamlit as st
from datetime import datetime
import base64

import os
from dotenv import load_dotenv

from conn_config import config_dict as cfg

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



# Convert image to Base64 for the app icon
def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Set custom app icon and page config
app_icon_base64 = image_to_base64(APP_ICON_PATH)
st.set_page_config(
    page_title="Cortex Analyst",
    page_icon=f"data:image/png;base64,{app_icon_base64}",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply custom CSS for dark theme
st.markdown(
    """
    <style>
        body {
            background-color: #1e1e1e;
            color: white;
        }
        .stMarkdown, .stCodeBlock {
            background-color: #333;
            color: white;
        }
        .stButton button {
            background-color: #090929;
            color: white;
        }
        .stSidebar {
            background-color: #252525;
        }
    </style>
    """,
    unsafe_allow_html=True,
)



# Functions for message processing
def send_message(prompt: str) -> Dict[str, Any]:
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
        return {**resp.json(), "request_id": request_id}  # type: ignore[arg-type]
    else:
        raise Exception(
            f"Failed request (id: {request_id}) with status {resp.status_code}: {resp.text}"
        )

def process_message(prompt: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.messages.append(
        {"role": "user", "content": [{"type": "text", "text": prompt}], "timestamp": timestamp}
    )
    with st.chat_message("user", avatar=USER_ICON_PATH):
        st.markdown(f"{prompt}")
    with st.chat_message("assistant", avatar=BOT_ICON_PATH):
        with st.spinner("The assistant is working on your question..."):
            response = send_message(prompt=prompt)
            request_id = response["request_id"]
            content = response["message"]["content"]
            display_content(content=content, request_id=request_id)
    st.session_state.messages.append(
        {"role": "assistant", "content": content, "request_id": request_id, "timestamp": timestamp}
    )
    st.session_state.chat_history.append({"question": prompt, "response": content, "timestamp": timestamp})

# def display_content(
#     content: List[Dict[str, str]],
#     request_id: Optional[str] = None,
# ) -> None:
#     if request_id:
#         with st.expander("Request ID", expanded=False):
#             st.markdown(request_id)
#     for item in content:
#         if item["type"] == "text":
#             st.markdown(f"![Bot Icon]({BOT_ICON_PATH_}) {item['text']}")

def display_content(
    content: List[Dict[str, str]],
    request_id: Optional[str] = None,
    message_index: Optional[int] = None,
) -> None:
    
    """Displays a content item for a message."""

    message_index = len(st.session_state.messages) or message_index

    # if request_id:
    #     with st.expander("Request ID", expanded=False):
    #         st.markdown(request_id)

    for item in content:
        
        if item["type"] == "text":
            st.markdown(item["text"])
        
        elif item["type"] == "suggestions":
            with st.expander("Suggestions", expanded=True):
                for suggestion_index, suggestion in enumerate(item["suggestions"]):
                    if st.button(suggestion, key=f"{message_index}_{suggestion_index}"):
                        st.session_state.active_suggestion = suggestion
        
        elif item["type"] == "sql":
            # with st.expander("Generated SQL Query", expanded=False):
            #     st.code(item["statement"], language="sql")
            
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


def img_to_base64(image_path):
    """Convert image to base64."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception as e:
        logging.error(f"Error converting image to base64: {str(e)}")
        return None
    


def main():

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.chat_history = []


    # Load and display sidebar image
    # img_path = "imgs/app_icon.png"
    img_base64 = img_to_base64(APP_ICON_PATH)
    if img_base64:
        st.sidebar.markdown(
            f'<img src="data:image/png;base64,{img_base64}" class="cover-glow">',
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("---")

    # Sidebar: About Section and Chat History
    st.sidebar.title("About")
    st.sidebar.info(
        f"""
        **{cfg["assistant_name"]}**  
        {cfg["app_description"]} 
        """
    )
    st.sidebar.title("Chat History")
    for i, chat in enumerate(st.session_state.chat_history):
        truncated_question = chat['question'] if len(chat['question']) < 20 else chat['question'][:20]
        if st.sidebar.button(f"{truncated_question} : ({chat['timestamp']})"):
            with st.sidebar.expander(f"Response ({chat['timestamp']})"):
                with st.chat_message("user", avatar=USER_ICON_PATH):
                    st.markdown(f"**Question**: {chat['question']}")
                with st.chat_message("assistant", avatar=BOT_ICON_PATH):
                    # st.markdown(f"**Response**: {chat['response']}")
                    

                    for item in chat['response']:
        
                        if item["type"] == "text":
                            st.markdown("**Response:**")
                            st.markdown(item["text"])
                        
                        # elif item["type"] == "suggestions":
                        #     # with st.expander("Suggestions", expanded=True):
                        #     st.markdown("**Suggestions:**")
                        #     for suggestion_index, suggestion in enumerate(item["suggestions"]):
                        #         if st.button(suggestion, key=f"{message_index}_{suggestion_index}"):
                        #             st.session_state.active_suggestion = suggestion
                        
                        elif item["type"] == "sql":
                            # with st.expander("Generated SQL Query", expanded=False):
                            # st.markdown("**SQL code:**")
                            # st.code(item["statement"], language="sql")
                            
                            # with st.expander("Query Results", expanded=True):
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





    # Main chat interface
    # st.markdown(
    #         f'<img src="data:image/png;base64,{img_base64}" class="cover-glow">',
    #         unsafe_allow_html=True,
    #     )
    st.title(cfg["assistant_name"])
    # st.markdown(f"Semantic Model: `{FILE}`")

    # Display existing messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=USER_ICON_PATH if message['role'] == "user" else BOT_ICON_PATH):
            display_content(content=message["content"])

    # Chat input
    if user_input := st.chat_input("Ask me a question."):
        process_message(prompt=user_input)

if __name__ == "__main__":
    main()