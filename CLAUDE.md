# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

Zoey 是一个基于阿里云 DashScope API 的多模态 AI 对话助手，使用 Gradio 构建 Web 界面，通过 OpenAI 兼容 SDK 调用 `qwen3.5-omni-plus-2026-03-15` 模型，支持文字、图片、音频输入。可部署到 Hugging Face Spaces。

## 常用命令

```bash
# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 启动应用
python -m zoey

# 代码检查
ruff check src/

# 自动修复
ruff check --fix src/

# 代码格式化
ruff format src/

# 运行测试
python -m pytest tests/ -v

# 运行测试（带覆盖率）
python -m pytest tests/ --cov=zoey --cov-report=term-missing

# 安装依赖
pip install -e ".[dev]"
```

## 架构说明

### 分层架构（`src/zoey/`）

```
app.py              UI 组件、事件绑定、localStorage 持久化
  ├── core/message.py    会话 CRUD、消息构建、模型约束校验
  │     └── core/processor.py   图片/音频 → base64 API 格式
  └── api/client.py      DashScope API 通信（流式回复）
```

### 核心数据流

1. **用户输入** → `gr.MultimodalTextbox` 收集文字 + 文件
2. **`on_user_message()`** → 追加消息到当前会话，自动生成标题（首条消息前 20 字）
3. **`on_submit()`** → `build_api_messages()` → `validate_input_types()` → `stream_chat()` 流式获取回复
4. **每次变更** → `storage_bridge.change` 回调 → `localStorage.setItem()` 持久化

### 会话模型

```python
{
    "id": "conv_xxx",
    "title": "自动生成标题",
    "messages": [{"role": "user"|"assistant", "content": str}, ...],
    "created_at": "ISO时间戳",
    "updated_at": "ISO时间戳",
}
```

localStorage 三个 key：`zoey_v2_conversations`、`zoey_v2_current_id`、`zoey_v2_system_prompt`

### 文件处理

| 类型 | 限制 | 处理方式 |
|------|------|---------|
| 图片 (jpg/png/gif/webp/bmp) | 10MB | RGBA→RGB，>1024px 缩放到 1024px，base64 编码 |
| 音频 (wav/mp3/m4a/aac/ogg/flac) | 25MB | base64 编码，data URL 前缀格式 |

**重要**：DashScope 音频 `input_audio.data` 字段需要 `data:audio/wav;base64,...` 格式（含 MIME 前缀），不是纯 base64。

### UI 布局

```
Row
├── Column(scale=1, min_width=260): 侧边栏
│   ├── Button "＋ 新对话"
│   ├── Radio 对话列表
│   ├── Button "🗑 删除当前对话"（二步确认）
│   ├── Textbox 系统提示词
│   └── 快捷问题 Buttons
└── Column(scale=3): 聊天区
    ├── Chatbot (type="messages")
    ├── MultimodalTextbox
    └── Textbox 状态栏
```

### 关键模式

- **流式响应**：`stream_chat()` 生成器 yield 文本增量，`on_submit()` 逐段更新 chatbot
- **懒加载客户端**：`_get_client()` 首次调用时创建 OpenAI 客户端
- **页面加载**：`block.load()` 必须放在所有组件定义之后才能引用 `chatbot`/`conv_radio`
- **删除二步确认**：第一次点击按钮变红显示"确认删除？"，第二次点击才执行
- **模型约束**：`validate_input_types()` 拦截多图、多音频、图+音混合（qwen-omni 系列限制）

## 注意事项

- `.env` 含 API 密钥 — 已在 `.gitignore`
- `pyproject.toml` 统一管理 ruff/pytest/coverage 配置
- Hugging Face Spaces 部署配置在 `.spaces/README.md`
- 测试 `coverage` 排除 `app.py` 和 `__main__.py`（UI 代码不适合单测），核心模块 `message.py`（84%）+ `processor.py`（90%）+ `client.py`（100%）总计 88%
