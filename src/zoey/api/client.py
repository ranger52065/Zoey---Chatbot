"""DashScope API 客户端"""

import os

from openai import OpenAI


def create_client() -> OpenAI:
    """创建 DashScope API 客户端（固定使用 qwen-omni-turbo）"""
    return OpenAI(
        api_key=os.environ["DASHSCOPE_API_KEY"],
        base_url=os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
    )
