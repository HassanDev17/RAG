from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class TokenUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class ChatResponse(BaseModel):
    role: str
    content: str
    token_usage: TokenUsage | None = None
    latency_ms: float
