"""共享测试 fixtures"""

import tempfile

import pytest
from PIL import Image


@pytest.fixture
def sample_text() -> str:
    return "你好，请介绍一下自己"


@pytest.fixture
def sample_history() -> list:
    return [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
    ]


@pytest.fixture
def small_png() -> str:
    """创建一个 100x100 的测试 PNG 图片"""
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f, format="PNG")
        return f.name


@pytest.fixture
def large_png() -> str:
    """创建一张超过 1024px 的图片（测试缩放）"""
    img = Image.new("RGB", (2000, 1500), color=(0, 255, 0))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f, format="PNG")
        return f.name


@pytest.fixture
def rgba_png() -> str:
    """创建一张 RGBA 图片"""
    img = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img.save(f, format="PNG")
        return f.name


@pytest.fixture
def small_wav() -> str:
    """创建一个最小的测试 WAV 文件"""
    import struct
    import wave

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name

    sample_rate = 8000
    duration = 0.1  # 100ms
    num_samples = int(sample_rate * duration)

    with wave.open(wav_path, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for _ in range(num_samples):
            wav.writeframes(struct.pack("<h", 0))

    return wav_path


@pytest.fixture
def empty_file() -> str:
    """创建一个空文件"""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        return f.name


@pytest.fixture(autouse=True)
def cleanup_temp_files():
    """自动清理临时文件"""
    yield
    import gc

    gc.collect()
