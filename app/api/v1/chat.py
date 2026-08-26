from fastapi import APIRouter

from app.schemas.chat import ChatMessage, ChatResponse
from app.services.chat import handle_chat

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(message: ChatMessage) -> ChatResponse:
    return handle_chat(message)
