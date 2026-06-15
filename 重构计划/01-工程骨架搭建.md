# 第一步：工程骨架搭建

> 依据 PRD 定稿版本设计

## 目标

在 Zoey 文件夹内重建完整的项目基础设施：源代码分层、测试框架、代码规范、版本控制、依赖管理、Spaces 部署配置。

旧文件全部清掉，从零开始搭骨架。

## 最终目录结构

```
Zoey/
├── .env.example              # 环境变量模板（不含真实密钥）
├── .gitignore                # 忽略规则
├── pyproject.toml            # 项目管理 + 工具配置
├── README.md                 # 项目说明
├── CHANGELOG.md              # 变更记录
│
├── src/
│   └── zoey/
│       ├── __init__.py
│       ├── __main__.py       # python -m zoey 入口
│       ├── app.py            # 应用启动 + Gradio UI 构建
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── message.py    # 消息模型、历史管理
│       │   └── processor.py  # 文件处理（图/音 → base64）
│       │
│       └── api/
│           ├── __init__.py
│           └── client.py     # DashScope API 客户端
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # 共享 fixtures
│   ├── test_processor.py     # 文件处理测试
│   └── test_message.py       # 消息模型测试
│
├── .spaces/                  # Hugging Face Spaces 配置
│   └── README.md             # Spaces 页面说明
│
└── 重构计划/                  # 本次重构的文档归档
    ├── 需求分析-PRD.md
    └── 01-工程骨架搭建.md
```

## 各文件内容

### pyproject.toml

```toml
[project]
name = "zoey"
version = "2.0.0"
description = "多模态 AI 对话助手"
requires-python = ">=3.11"
dependencies = [
    "gradio>=5.0",
    "openai>=2.0",
    "Pillow>=11",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-cov>=5",
    "ruff>=0.5",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "SIM"]

[tool.ruff.format]
quote-style = "double"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"

[tool.coverage.run]
source_pkgs = ["zoey"]

[tool.coverage.report]
fail_under = 80
```

### .env.example

```
DASHSCOPE_API_KEY="your-api-key-here"
DASHSCOPE_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
```

### .gitignore

```
.env
.venv/
__pycache__/
*.py[cod]
.ruff_cache/
.gradio/
.idea/
.vscode/
dist/
build/
*.egg-info/
.DS_Store
Thumbs.db
```

### src/zoey/\_\_init\_\_.py

```python
"""Zoey: 多模态 AI 对话助手"""
```

### src/zoey/\_\_main\_\_.py

```python
"""python -m zoey 入口"""

from zoey.app import main

main()
```

### src/zoey/app.py

```python
"""应用启动 + Gradio UI 构建"""

import os

import gradio as gr
from dotenv import load_dotenv

load_dotenv()


def create_ui() -> gr.Blocks:
    """构建 Gradio 界面"""
    with gr.Blocks(title="Zoey AI助手", theme=gr.themes.Soft()) as block:
        gr.Markdown("# Zoey 多模态 AI 助手")

        chatbot = gr.Chatbot(type="messages", height=500, show_copy_button=True)

        chat_input = gr.MultimodalTextbox(
            file_types=["image", ".wav", ".mp3", ".m4a"],
            file_count="multiple",
            placeholder="输入消息或上传文件...",
        )

        # 后续在 system_design 阶段完善组件和事件绑定
        # 当前只搭建骨架

    return block


def main() -> None:
    """启动应用"""
    block = create_ui()
    block.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)


if __name__ == "__main__":
    main()
```

> `app.py` 当前只包含最小可运行结构，UI 组件和事件绑定的完整实现在系统设计阶段补充。

### api/client.py

```python
"""DashScope API 客户端"""

from openai import OpenAI


def create_client() -> OpenAI:
    """创建 DashScope API 客户端"""
    import os
    return OpenAI(
        api_key=os.getenv("DASHSCOPE_API_KEY"),
        base_url=os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
    )
```

### core/message.py（占位）

```python
"""消息模型与历史管理"""
```

### core/processor.py（占位）

```python
"""文件处理：图片/音频 → base64"""
```

### tests/conftest.py

```python
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
```

### .spaces/README.md

```markdown
---
title: Zoey
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: "5.0"
app_file: src/zoey/app.py
pinned: false
---
```

## 需要删除的旧文件

以下文件是原版 Zoey 的，新架构不再需要：

```
Zoey.py          → 旧单文件应用
env_utils.py     → 改用 dotenv 直接加载
start.bat        → Windows 专属启动脚本，不再需要
.opencode/       → 含明文 API 密钥，删除
opencode.json    → 含明文 API 密钥，删除
```

`.env` 文件保留（内有 API 密钥），但会被 `.gitignore` 忽略。

## 执行步骤

确认后我将依次执行：

```
1. 删除旧文件（Zoey.py、env_utils.py、start.bat、.opencode/、opencode.json）
2. 创建目录结构（src/zoey/core、src/zoey/api、tests、.spaces）
3. 写入所有配置文件（pyproject.toml、.gitignore、.env.example）
4. 写入所有源码文件（__init__.py、__main__.py、app.py、api/client.py）
5. 写入占位模块（core/message.py、core/processor.py）
6. 写入测试骨架（conftest.py、test_processor.py、test_message.py）
7. 写入 Spaces 配置
8. 初始化 git（如尚未）
9. 安装依赖 pip install -e ".[dev]"
10. 验证 ruff check src/
```

## 不涉及的内容

- ⛔ 不实现业务逻辑（processor、message 的完整实现在编码阶段）
- ⛔ 不写完整 UI（app.py 只有最小结构，系统设计阶段补充）
- ⛔ 不写测试用例（只搭文件框架）
