# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目简介

Zoey 是一个基于阿里云 DashScope API（通义千问）的多模态 AI 对话助手，使用 Gradio 构建 Web 界面，通过 OpenAI 兼容 SDK 调用模型，支持文字、图片、音频输入。

## 常用命令

```bash
# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 启动应用
python Zoey/Zoey.py
# 或: start.bat

# 代码检查
ruff check Zoey/

# 自动修复
ruff check --fix Zoey/

# 代码格式化
ruff format Zoey/

# 安装依赖
pip install -r successful_requirements.txt
```

**测试：** 目前尚无 `tests/` 目录。后续添加测试后可参考以下命令：

```bash
pytest tests/ -v
pytest tests/test_file.py::test_func -v
```

## 架构说明

### 单文件应用（`Zoey/Zoey.py`，约 585 行）

核心流程：**UI 事件 → 消息处理 → API 调用 → 流式响应**。

### 模块职责

| 文件 | 职责 |
|---|---|
| `Zoey/Zoey.py` | 主应用：UI 界面、消息处理、API 集成 |
| `env_utils.py` | 通过 python-dotenv 从 `.env` 加载 `DASHSCOPE_API_KEY` |

### 数据流

1. **用户输入**：`gr.MultimodalTextbox` 收集文字 + 文件
2. **`add_message()`**：将用户内容追加到历史记录，格式为 `{"role": "user", "content": <str 或 tuple>}`。文件上传以 `(file_path,)` 元组形式暂存
3. **`build_content()`**：将历史记录转换为 API 兼容的内容列表。根据文件扩展名分发处理：
   - 图片 → `process_image()`（base64 编码，RGBA→RGB 转换，超过 1024px 缩放到 1024px）
   - 音频 → `process_audio()`（base64 编码，超过 25MB 时发出警告）
   - 视频 → 文字占位 `[上传视频: filename]`
4. **`submit_messages()`**：调用 `client.chat.completions.create()`（流式模式），每收到一个 chunk 就 `yield` 更新后的历史记录，Gradio 逐步更新界面
5. **`qwen-omni-turbo` 限制校验**：API 调用前检查——不支持多图、不支持多音频、不支持图+音混合输入

### UI 结构（Gradio Blocks）

```
Row
├── Column(scale=3): Chatbot, MultimodalTextbox, 清除/导出按钮
└── Column(scale=1): 模型选择器, 语音回复开关, 系统提示词, 快捷问题
```

事件链式绑定：`chat_input.submit(add_message).then(submit_messages).then(update_status)`

### 模型支持

| 模型 | 语音输出 | 说明 |
|---|---|---|
| `qwen-turbo` | 否 | 最快，日常对话 |
| `qwen-plus` | 否 | 均衡，通用场景 |
| `qwen-max` | 否 | 深度推理 |
| `qwen-omni-turbo` | 是 | 支持多模态输入，单文件约束 |

### 关键模式

- **流式响应**：`submit_messages()` 是生成器函数，每收到一个增量 chunk 就 `yield` 完整历史记录。`enable_audio=True` 时，音频数据随 chunk 的 `delta.audio` 到达，保存为 `response_audio.wav`
- **历史记录格式**：`[{"role": "user"|"assistant", "content": str}, ...]`
- **端口选择**：`find_available_port()` 从 7860 开始尝试最多 10 个端口
- **导出功能**：`export_history()` 将纯文字消息序列化为 JSON 文件，保存到 `Zoey/chat_history_<timestamp>.json`

### 注意事项

- `.env` 文件包含 API 密钥——已加入 `.gitignore`，切勿提交
- `opencode.json` 包含 DashScope WebParser 和 SpeechToText 的 MCP 配置
- `successful_requirements.txt` 编码有特殊字符，直接用于 pip 安装即可，无需手动修改
