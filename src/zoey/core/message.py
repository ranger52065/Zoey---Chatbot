"""会话管理：会话 CRUD、消息构建、输入约束校验"""

from datetime import datetime

from zoey.core.processor import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    process_audio,
    process_image,
)


def _generate_id() -> str:
    """生成唯一会话 ID"""
    import uuid

    return f"conv_{uuid.uuid4().hex[:12]}"


def create_conversation() -> dict:
    """创建新会话"""
    now = datetime.now().isoformat()
    return {
        "id": _generate_id(),
        "title": "新对话",
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }


def make_title(messages: list[dict]) -> str:
    """根据消息列表自动生成会话标题

    取第一条用户消息的前 20 个字符作为标题。
    如果是文件消息，用文件类型标注。
    """
    for msg in messages:
        if msg["role"] != "user":
            continue
        content = msg.get("content", "")
        if isinstance(content, str) and content.strip():
            text = content.strip()
            return text[:20] + ("..." if len(text) > 20 else "")
    return "新对话"


def get_last_user_messages(messages: list[dict]) -> list[dict] | None:
    """获取最后一次 AI 回复之后的所有用户消息

    用于从完整会话中提取需要发送给 API 的新消息。
    """
    if not messages:
        return None
    if messages[-1]["role"] == "assistant":
        return None

    last_assistant_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if messages[i]["role"] == "assistant":
            last_assistant_idx = i
            break

    if last_assistant_idx == -1:
        return messages
    return messages[last_assistant_idx + 1 :]


def build_content(user_messages: list[dict]) -> tuple:
    """将用户消息列表转为 API 兼容的内容列表

    Args:
        user_messages: 用户消息列表

    Returns:
        (content 列表, 输入类型统计)
        输入类型统计: {'images': int, 'audios': int, 'texts': int}
    """
    content = []
    input_types = {"images": 0, "audios": 0, "texts": 0}

    for msg in user_messages:
        raw = msg.get("content", "")

        if isinstance(raw, str):
            content.append({"type": "text", "text": raw})
            input_types["texts"] += 1

        elif isinstance(raw, tuple):
            file_path = raw[0]
            ext = file_path.lower()

            if ext.endswith(IMAGE_EXTENSIONS):
                img_dict = process_image(file_path)
                if img_dict:
                    content.append(img_dict)
                    input_types["images"] += 1

            elif ext.endswith(AUDIO_EXTENSIONS):
                audio_dict = process_audio(file_path)
                if audio_dict:
                    content.append(audio_dict)
                    input_types["audios"] += 1

            else:
                import os

                content.append(
                    {
                        "type": "text",
                        "text": f"[上传文件: {os.path.basename(file_path)}]",
                    }
                )
                input_types["texts"] += 1

    return content, input_types


def validate_input_types(input_types: dict) -> str | None:
    """验证 qwen-omni-turbo 输入约束

    Returns:
        不合法时返回错误提示文字，合法时返回 None
    """
    if input_types["images"] > 1:
        return "⚠️ 不支持多张图片同时输入，请每次只上传一张图片。"
    if input_types["audios"] > 1:
        return "⚠️ 不支持多个音频同时输入，请每次只上传一个音频。"
    if input_types["images"] > 0 and input_types["audios"] > 0:
        return "⚠️ 不支持图片和音频混合输入，请分开提交。"
    return None


def build_api_messages(
    conversation: dict,
    system_prompt: str | None = None,
) -> list[dict] | None:
    """将会话中的新消息转为 OpenAI API 兼容格式

    Args:
        conversation: 当前会话
        system_prompt: 可选系统提示词

    Returns:
        API 消息列表，无新消息时返回 None
    """
    user_messages = get_last_user_messages(conversation["messages"])
    if not user_messages:
        return None

    content, input_types = build_content(user_messages)
    if not content:
        return None

    # 校验输入约束
    error = validate_input_types(input_types)
    if error:
        # 将错误作为 assistant 消息追加到会话
        conversation["messages"].append({"role": "assistant", "content": error})
        return None

    api_messages = []
    if system_prompt and system_prompt.strip():
        api_messages.append({"role": "system", "content": system_prompt.strip()})

    api_messages.append({"role": "user", "content": content})
    return api_messages
