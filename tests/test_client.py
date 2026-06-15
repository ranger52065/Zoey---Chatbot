"""API 客户端模块测试"""

import os
from unittest.mock import MagicMock, patch

import pytest

from zoey.api.client import create_client, stream_chat


class TestCreateClient:
    def test_success_with_env_key(self):
        """环境变量中有 API 密钥时应成功创建客户端"""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "sk-test-key"}, clear=True):
            client = create_client()
            assert client is not None

    def test_raises_without_key(self):
        """环境变量中缺少 API 密钥时应抛出 RuntimeError"""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"),
        ):
            create_client()

    def test_uses_custom_base_url(self):
        """应使用 DASHSCOPE_BASE_URL 环境变量"""
        with patch.dict(
            os.environ,
            {
                "DASHSCOPE_API_KEY": "sk-test-key",
                "DASHSCOPE_BASE_URL": "https://custom.url/v1",
            },
            clear=True,
        ):
            from openai import OpenAI

            with patch.object(OpenAI, "__init__", return_value=None) as mock_init:
                create_client()
                mock_init.assert_called_once()
                _, kwargs = mock_init.call_args
                assert kwargs["base_url"] == "https://custom.url/v1"

    def test_default_base_url(self):
        """未设置 DASHSCOPE_BASE_URL 时应使用默认地址"""
        with patch.dict(
            os.environ,
            {
                "DASHSCOPE_API_KEY": "sk-test-key",
            },
            clear=True,
        ):
            from openai import OpenAI

            with patch.object(OpenAI, "__init__", return_value=None) as mock_init:
                create_client()
                _, kwargs = mock_init.call_args
                assert "dashscope.aliyuncs.com" in kwargs["base_url"]


class TestStreamChat:
    def test_yields_text_chunks(self):
        """应逐个 yield 文本增量"""
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="你好", audio=None))], usage=None),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="世界", audio=None))], usage=None),
            MagicMock(choices=[], usage=MagicMock(total_tokens=10)),
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_chunks

        messages = [{"role": "user", "content": "hi"}]
        result = list(stream_chat(mock_client, messages))
        assert result == ["你好", "世界"]

    def test_skips_usage_chunks(self):
        """usage chunk 应被跳过，不 yield 内容"""
        mock_chunks = [
            MagicMock(usage=MagicMock(total_tokens=10)),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="回复", audio=None))], usage=None),
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_chunks

        result = list(stream_chat(mock_client, [{"role": "user", "content": "hi"}]))
        assert result == ["回复"]

    def test_passes_messages_as_is(self):
        """传入的消息列表应原样发送"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = []

        sent = [
            {"role": "system", "content": "你是助手"},
            {"role": "user", "content": "hi"},
        ]
        list(stream_chat(mock_client, sent))

        call_kwargs = mock_client.chat.completions.create.call_args
        messages = call_kwargs[1]["messages"]
        assert messages == sent

    def test_stream_and_model_params(self):
        """请求应启用流式并使用指定模型"""
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = []

        list(stream_chat(mock_client, [{"role": "user", "content": "hi"}]))

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs[1]["stream"] is True
        assert call_kwargs[1]["model"] == "qwen3.5-omni-plus-2026-03-15"
