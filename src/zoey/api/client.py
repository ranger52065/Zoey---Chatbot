"""DashScope API 客户端（固定 qwen-omni-turbo）"""

import os
from collections.abc import Generator

from openai import OpenAI


def create_client() -> OpenAI:
    """创建 DashScope API 客户端"""
    api_key = os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("未找到 DASHSCOPE_API_KEY，请在 .env 文件中配置或设置环境变量")

    return OpenAI(
        api_key=api_key,
        base_url=os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
    )


def stream_chat(
    client: OpenAI,
    messages: list[dict],
    system_prompt: str | None = None,
) -> Generator[str, None, None]:
    """发送消息并流式获取回复

    Args:
        client: OpenAI 客户端实例
        messages: OpenAI 兼容的消息列表
        system_prompt: 可选系统提示词

    Yields:
        文本增量片段

    Raises:
        openai.AuthenticationError: API 密钥无效
        openai.APITimeoutError: 请求超时
        openai.RateLimitError: 触发限流
    """
    api_params: dict = {
        "model": "qwen-omni-turbo",
        "messages": [],
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    if system_prompt and system_prompt.strip():
        api_params["messages"].append(
            {
                "role": "system",
                "content": system_prompt.strip(),
            }
        )

    api_params["messages"].append({"role": "user", "content": messages})

    completion = client.chat.completions.create(**api_params)

    for chunk in completion:
        if hasattr(chunk, "usage") and chunk.usage:
            if chunk.usage.total_tokens:
                print(f"Token 使用: {chunk.usage}")
            continue

        if hasattr(chunk, "choices") and chunk.choices:
            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                yield delta.content
