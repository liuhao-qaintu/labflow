import os
from openai import OpenAI
from app.config import settings

_client = None

def get_client() ->OpenAI:
    global _client 
    if _client is None:
        api_key = settings.SILICONFLOW_API_KEY
        if not api_key:
            raise RuntimeError("没有获取到SILICONFLOW_API_KEY")
        _client = OpenAI(api_key=api_key,base_url=settings.LLM_BASE_URL)
    return _client

