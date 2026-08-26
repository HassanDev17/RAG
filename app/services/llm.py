from functools import lru_cache

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings

_PROVIDERS = {
    "google": ChatGoogleGenerativeAI,
    "anthropic": ChatAnthropic,
}


@lru_cache
def get_llm() -> BaseChatModel:
    settings = get_settings()
    provider_cls = _PROVIDERS[settings.llm_provider]
    return provider_cls(model=settings.llm_model, api_key=settings.llm_api_key or None)


def generate_reply(prompt: str) -> str:
    llm = get_llm()
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.text
