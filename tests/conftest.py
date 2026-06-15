"""共享测试 fixtures"""

import pytest


@pytest.fixture
def sample_text() -> str:
    return "你好，请介绍一下自己"


@pytest.fixture
def sample_history() -> list:
    return [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
    ]
