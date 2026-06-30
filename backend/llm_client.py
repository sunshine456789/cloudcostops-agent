from typing import Optional
from openai import OpenAI

from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


def has_llm_config() -> bool:
    return bool(OPENAI_API_KEY and OPENAI_API_KEY.strip())


def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    if not has_llm_config():
        raise RuntimeError("未配置 OPENAI_API_KEY，无法调用大模型。")

    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL
    )

    messages = []

    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })

    messages.append({
        "role": "user",
        "content": prompt
    })

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0.2,
        max_tokens=1800
    )

    return response.choices[0].message.content