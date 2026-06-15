"""消息管理模块测试"""

from zoey.core.message import (
    build_api_messages,
    build_content,
    create_conversation,
    get_last_user_messages,
    make_title,
    validate_input_types,
)


class TestCreateConversation:
    def test_returns_dict_with_required_keys(self):
        """新会话应包含所有必需字段"""
        conv = create_conversation()
        assert "id" in conv
        assert conv["id"].startswith("conv_")
        assert conv["title"] == "新对话"
        assert conv["messages"] == []
        assert "created_at" in conv
        assert "updated_at" in conv

    def test_unique_ids(self):
        """每次创建应生成唯一 ID"""
        ids = {create_conversation()["id"] for _ in range(100)}
        assert len(ids) == 100


class TestMakeTitle:
    def test_from_first_user_text(self):
        """应从第一条用户消息生成标题"""
        messages = [
            {"role": "user", "content": "介绍一下你自己"},
            {"role": "assistant", "content": "好的..."},
        ]
        assert make_title(messages) == "介绍一下你自己"

    def test_title_truncated_at_20_chars(self):
        """超过 20 字符应截断"""
        messages = [
            {"role": "user", "content": "请帮我解释一下量子力学的基本原理和它在现代科技中的应用"},
        ]
        title = make_title(messages)
        assert len(title) == 23  # 20 chars + "..."
        assert title.endswith("...")

    def test_ignores_assistant_messages(self):
        """不应从 AI 回复提取标题"""
        messages = [
            {"role": "assistant", "content": "你好！我是AI助手"},
        ]
        assert make_title(messages) == "新对话"

    def test_empty_messages(self):
        """空消息应返回默认标题"""
        assert make_title([]) == "新对话"

    def test_empty_user_content(self):
        """用户消息为空字符串时返回默认标题"""
        messages = [{"role": "user", "content": ""}]
        assert make_title(messages) == "新对话"


class TestGetLastUserMessages:
    def test_returns_all_when_no_assistant(self):
        """没有 AI 回复时应返回全部消息"""
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "user", "content": "在吗"},
        ]
        result = get_last_user_messages(messages)
        assert result == messages

    def test_returns_none_when_last_is_assistant(self):
        """最后一条是 AI 回复时应返回 None"""
        messages = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "在的"},
        ]
        assert get_last_user_messages(messages) is None

    def test_returns_messages_after_last_assistant(self):
        """应返回最后一次 AI 回复之后的消息"""
        messages = [
            {"role": "user", "content": "第一轮用户"},
            {"role": "assistant", "content": "第一轮回复"},
            {"role": "user", "content": "第二轮用户"},
        ]
        result = get_last_user_messages(messages)
        assert len(result) == 1
        assert result[0]["content"] == "第二轮用户"

    def test_empty_list(self):
        """空列表应返回 None"""
        assert get_last_user_messages([]) is None

    def test_single_message(self):
        """单条用户消息应返回自身"""
        messages = [{"role": "user", "content": "你好"}]
        result = get_last_user_messages(messages)
        assert result == messages


class TestBuildContent:
    def test_text_only(self):
        """纯文本消息应构建 text 类型内容"""
        messages = [{"role": "user", "content": "你好"}]
        content, types = build_content(messages)
        assert len(content) == 1
        assert content[0]["type"] == "text"
        assert content[0]["text"] == "你好"
        assert types["texts"] == 1

    def test_multiple_text_messages(self):
        """多条文字消息"""
        messages = [
            {"role": "user", "content": "第一句"},
            {"role": "user", "content": "第二句"},
        ]
        content, types = build_content(messages)
        assert len(content) == 2
        assert types["texts"] == 2

    def test_file_message_skipped_when_file_not_found(self):
        """文件不存在时跳过该文件"""
        messages = [
            {"role": "user", "content": ("/nonexistent/test.jpg",)},
        ]
        content, types = build_content(messages)
        assert types["images"] == 0
        assert len(content) == 0


class TestValidateInputTypes:
    def test_single_image_valid(self):
        """单张图片应通过校验"""
        assert validate_input_types({"images": 1, "audios": 0, "texts": 0}) is None

    def test_single_audio_valid(self):
        """单个音频应通过校验"""
        assert validate_input_types({"images": 0, "audios": 1, "texts": 0}) is None

    def test_multiple_images_invalid(self):
        """多张图片应返回错误"""
        result = validate_input_types({"images": 2, "audios": 0, "texts": 0})
        assert result is not None
        assert "多张图片" in result

    def test_multiple_audios_invalid(self):
        """多个音频应返回错误"""
        result = validate_input_types({"images": 0, "audios": 2, "texts": 0})
        assert result is not None
        assert "多个音频" in result

    def test_mixed_modalities_invalid(self):
        """图+音混合应返回错误"""
        result = validate_input_types({"images": 1, "audios": 1, "texts": 0})
        assert result is not None
        assert "混合输入" in result

    def test_all_zero_valid(self):
        """无输入应通过校验"""
        assert validate_input_types({"images": 0, "audios": 0, "texts": 0}) is None


class TestBuildApiMessages:
    def test_no_new_messages_returns_none(self):
        """最后一条是 AI 回复时应返回 None"""
        conv = create_conversation()
        conv["messages"] = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "在的"},
        ]
        result = build_api_messages(conv)
        assert result is None

    def test_includes_system_prompt(self):
        """包含系统提示词时应在最前面"""
        conv = create_conversation()
        conv["messages"] = [{"role": "user", "content": "你好"}]
        result = build_api_messages(conv, system_prompt="你是助手")
        assert result is not None
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "你是助手"

    def test_without_system_prompt(self):
        """不含系统提示词时不应有 system 消息"""
        conv = create_conversation()
        conv["messages"] = [{"role": "user", "content": "你好"}]
        result = build_api_messages(conv)
        assert result is not None
        assert result[0]["role"] == "user"

    def test_new_conversation_returns_none(self):
        """空会话应返回 None"""
        conv = create_conversation()
        result = build_api_messages(conv)
        assert result is None
