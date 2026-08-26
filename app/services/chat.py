from app.schemas.chat import ChatMessage, ChatResponse
from app.services.llm import generate_reply


def handle_chat(message: ChatMessage) -> ChatResponse:
    reply = generate_reply(message.content)
    return ChatResponse(role="assistant", content=reply)
