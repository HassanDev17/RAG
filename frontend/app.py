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

    .chat-meta {
        font-size: 0.76rem;
        color: #8a8a94;
        margin-top: 0.35rem;
    }

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


def render_message(role: str, content: str, meta: dict | None = None) -> None:
    body = html.escape(content).replace("\n", "<br>") if role == "user" else content

    meta_html = ""
    if meta:
        parts = []
        if meta.get("total_tokens") is not None:
            parts.append(
                f"{meta['total_tokens']} tokens "
                f"({meta.get('input_tokens', '?')} in / {meta.get('output_tokens', '?')} out)"
            )
        if meta.get("latency_ms") is not None:
            parts.append(f"{meta['latency_ms']:.0f} ms")
        if parts:
            meta_html = f'<div class="chat-meta">{" · ".join(parts)}</div>'

    st.markdown(
        f"""
        <div class="chat-row {role}">
            <div class="chat-bubble {role}">{body}{meta_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


for message in st.session_state.messages:
    render_message(message["role"], message["content"], message.get("meta"))

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

    meta = None
    try:
        response = requests.post(
            CHAT_ENDPOINT,
            json={"role": "user", "content": prompt},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        reply = data["content"]
        token_usage = data.get("token_usage") or {}
        meta = {
            "input_tokens": token_usage.get("input_tokens"),
            "output_tokens": token_usage.get("output_tokens"),
            "total_tokens": token_usage.get("total_tokens"),
            "latency_ms": data.get("latency_ms"),
        }
    except requests.RequestException as exc:
        reply = f"Sorry, something went wrong talking to the backend: {exc}"

    placeholder.empty()
    render_message("assistant", reply, meta)

    st.session_state.messages.append({"role": "assistant", "content": reply, "meta": meta})
