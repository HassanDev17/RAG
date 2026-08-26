from app.schemas.chat import ChatMessage, ChatResponse


def handle_chat(message: ChatMessage) -> ChatResponse:
    return ChatResponse(role=message.role, content=message.content)
