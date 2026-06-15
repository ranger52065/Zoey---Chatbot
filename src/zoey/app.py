"""Zoey 主应用：Gradio UI + 事件绑定 + localStorage 持久化"""

import json
import socket
from collections.abc import Generator
from datetime import datetime

import gradio as gr
from dotenv import load_dotenv

from zoey.api.client import create_client, stream_chat
from zoey.core.message import (
    build_api_messages,
    create_conversation,
    make_title,
)

load_dotenv()

_client = None

# ── localStorage 键名 ──────────────────────────

STORAGE_KEY = "zoey_v2_conversations"
STORAGE_CURRENT_ID = "zoey_v2_current_id"
STORAGE_SYSTEM_PROMPT = "zoey_v2_system_prompt"


# ── 工具函数 ───────────────────────────────────


def _get_client():
    """懒加载 API 客户端"""
    global _client
    if _client is None:
        _client = create_client()
    return _client


def _serialize(conversations: list[dict]) -> str:
    """将会话列表（纯文本消息）序列化为 JSON"""
    clean = []
    for conv in conversations:
        clean.append(
            {
                "id": conv["id"],
                "title": conv["title"],
                "messages": [
                    {"role": m["role"], "content": m["content"]}
                    for m in conv["messages"]
                    if isinstance(m.get("content"), str)
                ],
                "created_at": conv["created_at"],
                "updated_at": conv["updated_at"],
            }
        )
    return json.dumps(clean, ensure_ascii=False)


def _find_conv(conversations: list[dict], conv_id: str) -> dict | None:
    """按 ID 查找会话"""
    for c in conversations:
        if c["id"] == conv_id:
            return c
    return None


def _conv_titles(conversations: list[dict]) -> list[str]:
    """提取所有会话标题"""
    return [c["title"] for c in conversations]


def _format_error(error: Exception) -> str:
    """格式化错误为友好提示"""
    text = str(error).lower()
    if "authentication" in text or "invalid" in text or "api_key" in text:
        return "API 密钥无效，请检查 .env 文件中的 DASHSCOPE_API_KEY"
    if "timeout" in text:
        return "请求超时，请检查网络连接"
    if "rate" in text or "limit" in text:
        return "请求过于频繁，请稍后重试"
    if "audio" in text or "modality" in text:
        return "该模型不支持音频输入，已自动转为文字处理"
    # 返回原始错误便于排查
    return f"{str(error)[:200]}"


# ── 事件处理 ──────────────────────────────────


def on_page_load(storage_data: str, current_id_data: str, prompt_data: str) -> tuple:
    """页面加载时从 localStorage 恢复数据"""
    conversations = json.loads(storage_data) if storage_data else []
    current_id = current_id_data if current_id_data else ""
    system_prompt = prompt_data if prompt_data else ""

    if current_id and not _find_conv(conversations, current_id):
        current_id = ""

    if not conversations:
        conv = create_conversation()
        conversations.append(conv)
        current_id = conv["id"]

    current_conv = _find_conv(conversations, current_id)
    messages = current_conv["messages"] if current_conv else []
    current_title = current_conv["title"] if current_conv else ""

    return (
        conversations,
        current_id,
        system_prompt,
        messages,
        gr.Radio(choices=_conv_titles(conversations), value=current_title),
    )


def on_new_conversation(conversations: list[dict], current_id: str, system_prompt: str) -> tuple:
    """创建新会话"""
    conv = create_conversation()
    conversations.append(conv)
    current_id = conv["id"]
    titles = _conv_titles(conversations)
    return (
        conversations,
        current_id,
        gr.Radio(choices=titles, value=conv["title"]),
        [],
        "",
        "就绪",
        _serialize(conversations),
    )


def on_switch_conversation(conversations: list[dict], value: str) -> tuple:
    """切换会话"""
    for c in conversations:
        if c["title"] == value:
            return (c["id"], c["messages"], "", "就绪")
    return ("", [], "", "就绪")


def on_delete_conversation(conversations: list[dict], current_id: str) -> tuple:
    """删除当前会话"""
    if not current_id:
        return _empty_state()

    conversations = [c for c in conversations if c["id"] != current_id]

    if not conversations:
        conv = create_conversation()
        conversations.append(conv)
        current_id = conv["id"]
    else:
        current_id = conversations[0]["id"]

    current_conv = _find_conv(conversations, current_id)
    messages = current_conv["messages"] if current_conv else []
    titles = _conv_titles(conversations)

    return (
        conversations,
        current_id,
        messages,
        "",
        gr.Radio(choices=titles, value=current_conv["title"] if current_conv else ""),
        "已删除",
        _serialize(conversations),
    )


def _empty_state() -> tuple:
    """返回空状态"""
    return (
        [],
        "",
        [],
        "",
        gr.Radio(choices=[], value=None),
        "就绪",
        "[]",
    )


def on_user_message(conversations: list[dict], current_id: str, message: dict) -> tuple:
    """用户提交消息"""
    current_conv = _find_conv(conversations, current_id)
    if not current_conv:
        return (
            conversations,
            gr.Radio(choices=_conv_titles(conversations), value=None),
            [],
            gr.MultimodalTextbox(value=None, interactive=True),
            _serialize(conversations),
        )

    for file_data in message.get("files", []):
        file_path = file_data.path if hasattr(file_data, "path") else str(file_data)
        current_conv["messages"].append({"role": "user", "content": (file_path,)})

    if message.get("text") and message["text"].strip():
        text = message["text"].strip()
        current_conv["messages"].append({"role": "user", "content": text})

    if not current_conv["title"] or current_conv["title"] == "新对话":
        new_title = make_title(current_conv["messages"])
        if new_title != "新对话":
            current_conv["title"] = new_title

    current_conv["updated_at"] = datetime.now().isoformat()
    conv_title = current_conv["title"]
    titles = _conv_titles(conversations)

    return (
        conversations,
        gr.Radio(choices=titles, value=conv_title),
        current_conv["messages"],
        gr.MultimodalTextbox(value=None, interactive=True),
        _serialize(conversations),
    )


def on_submit(conversations: list[dict], current_id: str, system_prompt: str) -> Generator:
    """提交消息给 API 并流式获取回复"""
    current_conv = _find_conv(conversations, current_id)
    if not current_conv:
        yield (conversations, [], "就绪", _serialize(conversations))
        return

    # 检查当前模型是否支持音频
    from zoey.core.processor import AUDIO_EXTENSIONS
    has_audio = any(
        isinstance(m.get("content"), tuple)
        and str(m["content"][0]).lower().endswith(AUDIO_EXTENSIONS)
        for m in current_conv["messages"]
    )
    if has_audio:
        error_msg = "⚠️ 当前模型不支持音频输入，后续将接入语音转文字功能"
        current_conv["messages"].append({"role": "assistant", "content": error_msg})
        yield (
            conversations,
            current_conv["messages"],
            "就绪",
            _serialize(conversations),
        )
        return

    api_messages = build_api_messages(current_conv, system_prompt)
    if api_messages is None:
        yield (
            conversations,
            current_conv["messages"],
            "就绪",
            _serialize(conversations),
        )
        return

    # 占位
    current_conv["messages"].append({"role": "assistant", "content": "⏳ 正在思考..."})
    yield (conversations, current_conv["messages"], "处理中", _serialize(conversations))

    current_conv["messages"].pop()

    try:
        client = _get_client()
        current_conv["messages"].append({"role": "assistant", "content": ""})

        response_text = ""
        for text_chunk in stream_chat(client, api_messages):
            response_text += text_chunk
            current_conv["messages"][-1]["content"] = response_text
            yield (
                conversations,
                current_conv["messages"],
                "回复中",
                _serialize(conversations),
            )

        current_conv["updated_at"] = datetime.now().isoformat()
        yield (conversations, current_conv["messages"], "就绪", _serialize(conversations))

    except Exception as e:
        print(f"API 调用出错: {e}")
        import traceback

        traceback.print_exc()

        error_msg = f"❌ {_format_error(e)}"
        current_conv["messages"].append({"role": "assistant", "content": error_msg})
        yield (conversations, current_conv["messages"], "就绪", _serialize(conversations))


def on_preset_question(conversations: list[dict], current_id: str, question: str) -> tuple:
    """预设问题"""
    current_conv = _find_conv(conversations, current_id)
    if not current_conv:
        return (
            conversations,
            gr.Radio(choices=_conv_titles(conversations), value=None),
            [],
            _serialize(conversations),
        )

    current_conv["messages"].append({"role": "user", "content": question})

    if not current_conv["title"] or current_conv["title"] == "新对话":
        current_conv["title"] = question[:20] + ("..." if len(question) > 20 else "")

    current_conv["updated_at"] = datetime.now().isoformat()
    titles = _conv_titles(conversations)
    conv_title = current_conv["title"]

    return (
        conversations,
        gr.Radio(choices=titles, value=conv_title),
        current_conv["messages"],
        _serialize(conversations),
    )


# ── UI ────────────────────────────────────────

CSS = """
#sidebar { background: var(--background-fill-primary);
           border-right: 1px solid var(--border-color-primary); }
"""

PRESET_QUESTIONS = [
    "介绍一下你自己",
    "给我讲个笑话",
    "如何提高编程能力？",
]


def create_ui() -> gr.Blocks:
    """构建 Gradio 界面"""
    with gr.Blocks(
        title="Zoey AI 助手",
        theme=gr.themes.Soft(),
        css=CSS,
        fill_height=True,
    ) as block:
        # ── 状态 ──
        conversations_state = gr.State([])
        current_id_state = gr.State("")

        # ── localStorage 桥接 ──
        storage_bridge = gr.Textbox(visible=False)
        storage_current_id = gr.Textbox(visible=False)
        storage_prompt = gr.Textbox(visible=False)

        # ── 页面加载 ──
        block.load(
            fn=on_page_load,
            inputs=[storage_bridge, storage_current_id, storage_prompt],
            outputs=[
                conversations_state,
                current_id_state,
                storage_prompt,
                gr.Chatbot(type="messages", visible=False),
                gr.Radio(visible=False),
            ],
            js="""
            () => {
                return [
                    localStorage.getItem('zoey_v2_conversations') || '[]',
                    localStorage.getItem('zoey_v2_current_id') || '',
                    localStorage.getItem('zoey_v2_system_prompt') || ''
                ];
            }
            """,
        )

        # ── 布局 ──
        gr.Markdown("# 🤖 Zoey 多模态 AI 助手")

        with gr.Row(equal_height=False):
            # 左侧边栏
            with gr.Column(scale=1, min_width=260, elem_id="sidebar"):
                new_btn = gr.Button("＋ 新对话", variant="primary", size="lg")

                conv_radio = gr.Radio(
                    choices=[],
                    label="对话列表",
                    interactive=True,
                    container=True,
                )

                delete_btn = gr.Button("🗑 删除当前对话", size="sm")

                system_prompt = gr.Textbox(
                    label="系统提示词",
                    placeholder="设置 AI 的角色和行为...",
                    value="你是一个友好、专业的 AI 助手，请用简洁清晰的语言回答问题。",
                    lines=3,
                )

                gr.Markdown("### 💡 快捷问题")
                preset_buttons = []
                for q in PRESET_QUESTIONS:
                    btn = gr.Button(q, size="sm")
                    preset_buttons.append((btn, q))

            # 右侧聊天区
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    type="messages",
                    height=500,
                    show_copy_button=True,
                    label="对话窗口",
                    avatar_images=(None, "🤖"),
                )

                chat_input = gr.MultimodalTextbox(
                    file_types=["image", ".wav", ".mp3", ".m4a"],
                    file_count="multiple",
                    placeholder="输入消息或上传文件（图片/音频）...",
                    sources=["microphone", "upload"],
                )

                status_text = gr.Textbox(
                    label="状态",
                    value="就绪",
                    interactive=False,
                    show_label=False,
                )

        # ── 事件绑定 ──

        # 新建对话
        new_btn.click(
            fn=on_new_conversation,
            inputs=[conversations_state, current_id_state, system_prompt],
            outputs=[
                conversations_state,
                current_id_state,
                conv_radio,
                chatbot,
                chat_input,
                status_text,
                storage_bridge,
            ],
        )

        # 切换对话
        conv_radio.change(
            fn=on_switch_conversation,
            inputs=[conversations_state, conv_radio],
            outputs=[current_id_state, chatbot, chat_input, status_text],
        )

        # 删除对话
        delete_btn.click(
            fn=on_delete_conversation,
            inputs=[conversations_state, current_id_state],
            outputs=[
                conversations_state,
                current_id_state,
                chatbot,
                chat_input,
                conv_radio,
                status_text,
                storage_bridge,
            ],
            js="""
            () => {
                if (!confirm('确定要删除当前对话吗？此操作不可撤回。')) {
                    return null;
                }
            }
            """,
        )

        # 提交消息
        chat_input.submit(
            fn=on_user_message,
            inputs=[conversations_state, current_id_state, chat_input],
            outputs=[
                conversations_state,
                conv_radio,
                chatbot,
                chat_input,
                storage_bridge,
            ],
        ).then(
            fn=on_submit,
            inputs=[conversations_state, current_id_state, system_prompt],
            outputs=[conversations_state, chatbot, status_text, storage_bridge],
        )

        # 系统提示词变更 → 持久化到 localStorage
        system_prompt.change(
            fn=lambda p: p,
            inputs=[system_prompt],
            outputs=[storage_prompt],
            js="""
            (prompt) => {
                localStorage.setItem('zoey_v2_system_prompt', prompt);
                return prompt;
            }
            """,
        )

        # 预设问题
        for btn, question in preset_buttons:
            btn.click(
                fn=on_preset_question,
                inputs=[conversations_state, current_id_state, gr.State(question)],
                outputs=[
                    conversations_state,
                    conv_radio,
                    chatbot,
                    storage_bridge,
                ],
            ).then(
                fn=on_submit,
                inputs=[conversations_state, current_id_state, system_prompt],
                outputs=[conversations_state, chatbot, status_text, storage_bridge],
            )

    return block


# ── 启动 ──


def _find_port(start: int = 7860, max_attempts: int = 10) -> int:
    """查找可用端口"""
    import socket as _socket

    for port in range(start, start + max_attempts):
        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"在 {start}~{start + max_attempts - 1} 范围内找不到可用端口")


def main() -> None:
    """启动应用"""
    print("=" * 50)
    print("Zoey 多模态 AI 助手 v2 启动中...")
    print("=" * 50)

    block = create_ui()
    port = _find_port()
    local_ip = socket.gethostbyname(socket.gethostname())
    print(f"\n[本地]  http://127.0.0.1:{port}")
    print(f"[局域网] http://{local_ip}:{port}")
    print("=" * 50)

    block.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
