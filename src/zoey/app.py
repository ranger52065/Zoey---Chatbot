"""应用启动 + Gradio UI 构建"""

import gradio as gr
from dotenv import load_dotenv

load_dotenv()


def create_ui() -> gr.Blocks:
    """构建 Gradio 界面"""
    with gr.Blocks(title="Zoey AI助手", theme=gr.themes.Soft()) as block:
        gr.Markdown("# Zoey 多模态 AI 助手")

        chatbot = gr.Chatbot(type="messages", height=500, show_copy_button=True)  # noqa: F841

        chat_input = gr.MultimodalTextbox(  # noqa: F841
            file_types=["image", ".wav", ".mp3", ".m4a"],
            file_count="multiple",
            placeholder="输入消息或上传文件...",
        )

        # 系统设计阶段完善组件和事件绑定
        # 当前只搭建骨架占位

    return block


def main() -> None:
    """启动应用"""
    block = create_ui()
    block.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)


if __name__ == "__main__":
    main()
