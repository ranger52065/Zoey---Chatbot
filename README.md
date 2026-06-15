# Zoey - 多模态 AI 对话助手 🤖

基于阿里云 DashScope API 的多模态 AI 对话助手，使用 Gradio 构建 Web 界面，支持文字、图片、音频输入。

## 功能

- ✏️ 文字对话（流式输出）
- 🖼️ 图片理解
- 🎤 音频输入（麦克风 / 文件上传）
- 💬 多会话管理（侧边栏切换、新建、删除）
- 🏷️ 自动生成对话标题
- 💾 刷新不丢失（浏览器 localStorage 持久化）
- 📱 移动端适配

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/ranger52065/Zoey---Chatbot.git
cd Zoey---Chatbot

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 3. 安装依赖
pip install -e ".[dev]"

# 4. 配置 API 密钥
# 复制 .env.example 为 .env，填入你的阿里云百炼 API 密钥

# 5. 启动
python -m zoey
```

浏览器打开 `http://127.0.0.1:7860` 即可使用。

## 部署到 Hugging Face Spaces

1. 在 [huggingface.co](https://huggingface.co) 创建 Space（SDK: Gradio）
2. 关联此 GitHub 仓库
3. 在 Settings → Repository secrets 添加 `DASHSCOPE_API_KEY`
4. 自动部署完成

## 技术栈

- **前端/后端**：Gradio 5
- **模型**：通义千问 qwen3.5-omni-plus（阿里云 DashScope）
- **SDK**：OpenAI Python SDK
- **图片处理**：Pillow
- **测试**：pytest + coverage（88%）
- **代码规范**：Ruff

## 项目结构

```
Zoey/
├── app.py                  # 部署入口
├── requirements.txt        # 依赖
├── pyproject.toml          # 项目管理
├── src/zoey/
│   ├── app.py              # UI + 事件 + 持久化
│   ├── api/client.py       # API 通信
│   └── core/
│       ├── message.py      # 会话管理
│       └── processor.py    # 文件处理
└── tests/                  # 42 个测试
```
