"""文件处理：图片/音频 → base64 API 格式"""

import base64
import io
import os

from PIL import Image

# 文件大小限制（单位：MB）
MAX_IMAGE_SIZE_MB = 10
MAX_AUDIO_SIZE_MB = 25

# 图片支持的文件后缀
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
# 音频支持的文件后缀
AUDIO_EXTENSIONS = (".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac")


class FileTooLargeError(Exception):
    """文件超过大小限制"""


def _check_file_size(file_path: str, max_mb: int, file_type: str) -> None:
    """检查文件是否超过大小限制"""
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > max_mb:
        raise FileTooLargeError(
            f"{file_type}文件过大 ({size_mb:.1f}MB)，超过 {max_mb}MB 限制，请压缩后重传"
        )


def process_image(file_path: str) -> dict | None:
    """将图片转换为 base64 API 格式

    Args:
        file_path: 图片文件路径

    Returns:
        API 兼容的图片字典，失败返回 None
    """
    try:
        _check_file_size(file_path, MAX_IMAGE_SIZE_MB, "图片")
    except (FileTooLargeError, FileNotFoundError, OSError) as e:
        print(f"图片处理失败: {e}")
        return None

    try:
        with Image.open(file_path) as img:
            img_format = img.format if img.format else "JPEG"

            # RGBA → RGB（JPEG 不支持透明度）
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
                img_format = "JPEG"
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # 超过 1024px 按比例缩放
            max_size = 1024
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            buffered = io.BytesIO()
            img.save(buffered, format=img_format, quality=85)
            img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{img_format.lower()};base64,{img_base64}",
                    "detail": "low",
                },
            }
    except Exception as e:
        print(f"图片处理失败 {file_path}: {e}")
        return None


def process_audio(file_path: str) -> dict | None:
    """将音频转换为 base64 API 格式

    Args:
        file_path: 音频文件路径

    Returns:
        API 兼容的音频字典，失败返回 None
    """
    try:
        _check_file_size(file_path, MAX_AUDIO_SIZE_MB, "音频")
    except (FileTooLargeError, FileNotFoundError, OSError) as e:
        print(f"音频处理失败: {e}")
        return None

    try:
        with open(file_path, "rb") as f:
            audio_data = f.read()

        audio_format = os.path.splitext(file_path)[1].lower().lstrip(".")
        if not audio_format:
            audio_format = "wav"

        audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        return {
            "type": "input_audio",
            "input_audio": {
                "data": audio_base64,
                "format": audio_format,
            },
        }
    except Exception as e:
        print(f"音频处理失败 {file_path}: {e}")
        return None
