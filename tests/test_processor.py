"""文件处理模块测试"""

import pytest

from zoey.core.processor import (
    process_audio,
    process_image,
)


class TestProcessImage:
    def test_rgb_image_success(self, small_png):
        """正常 RGB 图片应返回 API 兼容格式"""
        result = process_image(small_png)
        assert result is not None
        assert result["type"] == "image_url"
        assert "image_url" in result
        assert result["image_url"]["url"].startswith("data:image/png;base64,")
        assert result["image_url"]["detail"] == "low"

    def test_large_image_resized(self, large_png):
        """大图应缩放到不超过 1024px"""
        from PIL import Image

        # 先获取原始尺寸
        with Image.open(large_png) as img:
            original_w, original_h = img.size
            assert max(original_w, original_h) > 1024

        result = process_image(large_png)
        assert result is not None

        # 验证缩放后尺寸
        import base64
        import io

        data_url = result["image_url"]["url"]
        base64_data = data_url.split(",", 1)[1]
        image_data = base64.b64decode(base64_data)
        with Image.open(io.BytesIO(image_data)) as img:
            assert max(img.size) <= 1024

    def test_rgba_converted_to_rgb(self, rgba_png):
        """RGBA 图片应转为 RGB（JPEG 格式）"""
        result = process_image(rgba_png)
        assert result is not None
        # RGBA → RGB 后强制转 JPEG
        assert result["image_url"]["url"].startswith("data:image/jpeg;base64,")

    def test_nonexistent_file(self):
        """不存在的文件应返回 None"""
        result = process_image("/nonexistent/path/image.jpg")
        assert result is None

    def test_corrupted_file(self, empty_file):
        """损坏文件应返回 None"""
        result = process_image(empty_file)
        assert result is None

    @pytest.mark.skip(reason="需要 10MB+ 真实文件，跳过大小测试")
    def test_oversized_file(self):
        """超过大小限制的文件应返回 None"""
        pass


class TestProcessAudio:
    def test_audio_success(self, small_wav):
        """正常音频应返回 API 兼容格式"""
        result = process_audio(small_wav)
        assert result is not None
        assert result["type"] == "input_audio"
        assert "input_audio" in result
        assert "data" in result["input_audio"]
        assert "format" in result["input_audio"]
        assert result["input_audio"]["format"] == "wav"

    def test_nonexistent_file(self):
        """不存在的文件应返回 None"""
        result = process_audio("/nonexistent/path/audio.wav")
        assert result is None

    def test_corrupted_file(self, empty_file):
        """空文件通过 base64 编码（不是音频也能处理，返回格式为 txt）"""
        result = process_audio(empty_file)
        assert result is not None
        assert result["input_audio"]["format"] == "txt"
