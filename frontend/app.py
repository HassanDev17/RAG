import html
import os

import requests
import streamlit as st

API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT = f"{API_BASE_URL}/api/v1/chat"

st.set_page_config(page_title="RAG Chat", page_icon="💬", layout="centered")

st.markdown(
    """
    <style>
    #MainMenu, footer, header { visibility: hidden; }

    .block-container {
        max-width: 780px;
        padding-top: 2.5rem;
        padding-bottom: 8rem;
    }

    .app-title {
        font-size: 1.4rem;
        font-weight: 600;
        color: #ececec;
        margin-bottom: 1.75rem;
    }

    .chat-row {
        display: flex;
        margin-bottom: 1.4rem;
    }
    .chat-row.user { justify-content: flex-end; }
    .chat-row.assistant { justify-content: flex-start; }

    .chat-bubble {
        max-width: 75%;
        line-height: 1.55;
        font-size: 0.96rem;
    }
    .chat-bubble.user {
        background-color: #2f2f2f;
        color: #ececec;
        border-radius: 18px;
        padding: 0.6rem 1rem;
    }
    .chat-bubble.assistant {
        background-color: transparent;
        color: #d9d9e0;
        padding: 0.1rem 0;
    }
    .chat-bubble p { margin: 0 0 0.5rem 0; }
    .chat-bubble p:last-child { margin-bottom: 0; }

    div[data-testid="stChatInput"] {
        max-width: 780px;
        margin: 0 auto;
    }
    div[data-testid="stChatInput"] textarea {
        border-radius: 24px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="app-title">💬 RAG Chat</div>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_message(role: str, content: str) -> None:
    body = html.escape(content).replace("\n", "<br>") if role == "user" else content
    st.markdown(
        f"""
        <div class="chat-row {role}">
            <div class="chat-bubble {role}">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


for message in st.session_state.messages:
    render_message(message["role"], message["content"])

prompt = st.chat_input("Ask a question...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    render_message("user", prompt)

    placeholder = st.empty()
    with placeholder:
        st.markdown(
            '<div class="chat-row assistant"><div class="chat-bubble assistant">Thinking...</div></div>',
            unsafe_allow_html=True,
        )

    try:
        response = requests.post(
            CHAT_ENDPOINT,
            json={"role": "user", "content": prompt},
            timeout=60,
        )
        response.raise_for_status()
        reply = response.json()["content"]
    except requests.RequestException as exc:
        reply = f"Sorry, something went wrong talking to the backend: {exc}"

    placeholder.empty()
    render_message("assistant", reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
