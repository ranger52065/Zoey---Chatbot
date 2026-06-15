# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

Zoey 是一个基于阿里云 DashScope API 的多模态 AI 对话助手，使用 Gradio 构建 Web 界面，通过 OpenAI 兼容 SDK 调用模型，支持文字、图片、音频输入。

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
python -m pytest tests/ --cov=zoey

# 安装依赖
pip install -e ".[dev]"
```

## 架构说明

### 分层架构（src/zoey/）

```
app.py           UI 组件、事件绑定、localStorage 操作
  ├── core/message.py    会话 CRUD、消息构建、输入约束校验
  │     └── core/processor.py   图片/音频 → base64（含文件大小限制）
  └── api/client.py      DashScope API 通信（固定模型，流式回复）
```

### 核心数据流

1. **用户输入**：`gr.MultimodalTextbox` 收集文字 + 文件
2. **`on_user_message()`**：将消息追加到当前会话，自动生成标题
3. **`on_submit()`** → `build_api_messages()` → 校验约束 → `stream_chat()`：调用 API 流式获取回复
4. 每次变化同步到 `localStorage`（`zoey_v2_conversations`、`zoey_v2_current_id`、`zoey_v2_system_prompt`）

### 多会话管理

- 侧边栏 `conv_radio` 列出所有会话标题，点击切换
- 新建按钮创建空会话，自动生成标题（取首条用户消息前20字）
- 删除按钮二步确认：第一次变红"确认删除？"，第二次执行删除
- 所有会话持久化在浏览器 localStorage，刷新不丢

### 关键模式

- **流式响应**：`stream_chat()` 是生成器，yield 文本增量，`on_submit()` 逐段更新 chatbot
- **会话格式**：`{"id", "title", "messages": [{"role", "content"}, ...], "created_at", "updated_at"}`
- **文件处理**：图片（RGBA→RGB，缩放 ≤1024px），音频（data URL 前缀格式）
- **懒加载客户端**：`_get_client()` 首次调用时创建 OpenAI 客户端

### UI 结构（Gradio Blocks）

```
Row
├── Column(scale=1, min_width=260): 侧边栏
│   ├── Button "＋ 新对话"
│   ├── Radio 对话列表
│   ├── Button "🗑 删除当前对话"
│   ├── Textbox 系统提示词
│   └── Markdown 快捷问题 + Buttons
└── Column(scale=3): 聊天区
    ├── Chatbot
    ├── MultimodalTextbox
    └── Textbox 状态栏
```

### 音频输入踩坑记录

DashScope 的 `input_audio` 格式和 OpenAI 标准不同：
- `data` 字段需要 `data:audio/wav;base64,...` 前缀（data URL 格式），不是纯 base64
- 模型名 `qwen3.5-omni-plus-2026-03-15` 支持多模态

### 注意事项

- `.env` 文件包含 API 密钥——已加入 `.gitignore`，切勿提交
- `pyproject.toml` 配置了 ruff、pytest、coverage（核心模块 ≥ 80%）
- Hugging Face Spaces 部署配置在 `.spaces/README.md`
