"""Zoey 根入口 — 适配 Hugging Face Spaces 部署"""

import sys
from pathlib import Path

# 将 src 目录加入模块搜索路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from zoey.app import main

main()
