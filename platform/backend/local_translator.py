"""本地中→英翻译（离线，Helsinki-NLP/opus-mt-zh-en）。

用 transformers MarianMT 在 CPU 上懒加载模型，短文本翻译延迟可忽略。
避免依赖任何外部翻译 API，彻底消除网络波动导致的语义错乱。

模型权重位于 platform/backend/models/opus-mt-zh-en/，
其中 model.safetensors 由原 pytorch_model.bin 转换而来（解决共享权重 + torch>=2.6 限制）。
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

_MODEL_DIR = Path(__file__).resolve().parent / "models" / "opus-mt-zh-en"
_model = None
_tokenizer = None
_lock = threading.Lock()


def _load():
    """懒加载翻译模型（线程安全，仅首次调用时加载）。"""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    with _lock:
        if _model is not None:
            return _model, _tokenizer

        import torch
        from transformers import MarianMTModel, MarianTokenizer

        if not _MODEL_DIR.is_dir():
            raise RuntimeError(f"本地翻译模型目录不存在：{_MODEL_DIR}")

        logging.info("加载本地翻译模型 opus-mt-zh-en（CPU）...")
        _tokenizer = MarianTokenizer.from_pretrained(str(_MODEL_DIR), local_files_only=True)
        _model = MarianMTModel.from_pretrained(str(_MODEL_DIR), local_files_only=True)
        _model.eval()
        logging.info("本地翻译模型加载完成")
        return _model, _tokenizer


def translate_zh_to_en(text: str) -> str:
    """将中文文本翻译为英文（本地离线）。

    返回翻译结果（保留原句首尾大小写、去掉多余句点）。
    """
    import torch

    model, tokenizer = _load()
    inputs = tokenizer(text, return_tensors="pt", padding=True)
    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=128)
    result = tokenizer.decode(output[0], skip_special_tokens=True).strip()
    # 去掉 opus-mt 常带的末尾句点
    return result.rstrip(".")
