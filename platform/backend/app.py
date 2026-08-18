"""Flask API: local ComfyUI/SDXL text-to-image plus local Hunyuan3D 2.0 image-to-3D."""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

import shutil
import subprocess

import httpx
import urllib.parse
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "static" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__, static_folder=str(BASE_DIR / "static"), static_url_path="/static")
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_ORIGIN", "*")}})

# ── ComfyUI 配置 ────────────────────────────────────────────
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
COMFYUI_CHECKPOINT = os.getenv("COMFYUI_CHECKPOINT", "sd_xl_base_1.0.safetensors")
COMFYUI_TIMEOUT = float(os.getenv("COMFYUI_TIMEOUT", "600"))
COMFYUI_WIDTH = int(os.getenv("COMFYUI_WIDTH", "1024"))
COMFYUI_HEIGHT = int(os.getenv("COMFYUI_HEIGHT", "1024"))

# ── Hunyuan3D 2.0 配置 ────────────────────────────────────────
HUNYUAN3D_PYTHON = os.getenv("HUNYUAN3D_PYTHON", "python")
HUNYUAN3D_MODEL = os.getenv("HUNYUAN3D_MODEL", "tencent/Hunyuan3D-2mini")
HUNYUAN3D_STEPS = int(os.getenv("HUNYUAN3D_STEPS", "30"))
HUNYUAN3D_TEX = os.getenv("HUNYUAN3D_TEX", "true").lower() in ("1", "true", "yes")
HUNYUAN3D_OCTREE_RES = int(os.getenv("HUNYUAN3D_OCTREE_RES", "256"))
HUNYUAN3D_TIMEOUT = int(os.getenv("HUNYUAN3D_TIMEOUT", "600"))


def _json_body() -> dict[str, Any]:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def _error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


# ── 中译英 ──────────────────────────────────────────────────

import re

def _translate_to_english(text: str) -> str:
    """中文提示词转英文。

    优先走本地离线词典（确定、稳定），未覆盖的词再尝试 MyMemory 兜底；
    兜底也失败时抛错，绝不把中文原文静默喂给 SDXL 的英文 CLIP
    （否则会因 CLIP 不懂中文而产生语义错乱，如「椅子」生成「摩托车」）。
    """
    from zh_en_dict import translate_zh_to_en

    if not re.search(r'[一-鿿]', text):
        return text

    # 1) 本地词典优先
    dict_translated = translate_zh_to_en(text)
    if not re.search(r'[一-鿿]', dict_translated):
        # 词典已完全覆盖，无残留中文
        logging.info("Dict translated prompt: %s -> %s", text, dict_translated)
        return dict_translated

    # 2) 残留中文，尝试 MyMemory 兜底
    try:
        encoded = urllib.parse.quote(text)
        url = f"https://api.mymemory.translated.net/get?q={encoded}&langpair=zh-CN%7Cen"
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        translated = data.get("responseData", {}).get("translatedText", "")
        if translated:
            # 去掉 MyMemory 加的冠词 (a/an)，避免干扰 CLIP 权重语法
            translated = re.sub(r'^(an?)\s+', '', translated)
            logging.info("MyMemory translated prompt: %s -> %s", text, translated)
            return translated
        raise RuntimeError("empty translation")
    except Exception as exc:
        # 3) 兜底也失败：明确抛错，拒绝用中文喂 CLIP
        logging.error("Translation failed for: %s (%s)", text, exc)
        raise RuntimeError(
            f"提示词翻译失败，请改用英文输入或换个说法：{text}"
        ) from exc


# ── ComfyUI 工作流 ──────────────────────────────────────────

def _comfy_workflow(subject: str, adjective: str, seed: int) -> dict[str, dict[str, Any]]:
    """SDXL txt2img workflow — 主体高权重 (1.4)、形容词低权重 (1.1)，减少语义误判。

    主体与修饰分开喂给 CLIP，模型先锁定「物体是什么」，再叠加「长什么样」，
    避免一整句话被整体打包导致主体不突出或形容词被误读为额外物体。
    """
    subject_en = _translate_to_english(subject)
    subject_part = f"({subject_en}:1.4)"

    adjective_en = _translate_to_english(adjective).strip() if adjective else ""
    adjective_part = f", ({adjective_en}:1.1)" if adjective_en else ""

    # 不放否定语在正向 prompt 中；去掉 "studio product photography"
    # — 对小物件有偏见，大型/复杂物体生成不准
    positive = (
        subject_part + adjective_part + ", "
        "professional photograph, centered, full view, "
        "clean background, high detail, "
        f"uid:{seed}"   # 防止 ComfyUI 缓存复用（每次 seed 不同，hash 不同）
    )
    negative = (
        "text, watermark, logo, signature, letters, numbers, "
        "people, hands, fingers, faces, "
        "multiple objects, clutter, messy, crowded, "
        "cropped, blurry, low quality, deformed, distorted, ugly"
    )
    # DPM++ 2M Karras 对 SDXL 语义遵循度更好
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": COMFYUI_CHECKPOINT}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["4", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": COMFYUI_WIDTH, "height": COMFYUI_HEIGHT, "batch_size": 1}},
        "3": {"class_type": "KSampler", "inputs": {"seed": seed, "steps": 30, "cfg": 8.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "3d_maker", "images": ["8", 0]}},
    }


def _wait_for_comfy_image(prompt_id: str) -> tuple[str, str, str]:
    deadline = time.monotonic() + COMFYUI_TIMEOUT
    with httpx.Client(timeout=30) as client:
        while time.monotonic() < deadline:
            response = client.get(f"{COMFYUI_URL}/history/{prompt_id}")
            response.raise_for_status()
            history = response.json().get(prompt_id)
            if history and history.get("status", {}).get("status_str") == "error":
                raise RuntimeError("ComfyUI 工作流执行失败")
            if history and history.get("outputs"):
                for node_output in history["outputs"].values():
                    images = node_output.get("images", [])
                    if images:
                        image = images[0]
                        return image["filename"], image.get("subfolder", ""), image.get("type", "output")
            time.sleep(1.5)
    raise TimeoutError(f"ComfyUI 任务超过 {int(COMFYUI_TIMEOUT)} 秒仍未完成")


# ── 路由 ─────────────────────────────────────────────────────

@app.get("/")
def index():
    return send_from_directory(BASE_DIR.parent / "frontend", "test.html")


@app.get("/api/health")
def health():
    comfy_ok = False
    try:
        comfy_ok = httpx.get(f"{COMFYUI_URL}/system_stats", timeout=3).is_success
    except Exception:
        pass
    return jsonify({
        "success": True,
        "image_backend": "comfyui-sdxl",
        "comfyui_url": COMFYUI_URL,
        "comfyui_ok": comfy_ok,
        "3d_backend": "hunyuan3d",
        "hunyuan3d_model": HUNYUAN3D_MODEL,
    })


@app.post("/api/generate-image")
def generate_image():
    data = _json_body()
    subject = str(data.get("subject", "")).strip()
    adjective = str(data.get("adjective", "")).strip()
    # 兼容旧版单输入框：只传 prompt 时，整个描述当作主体
    if not subject:
        subject = str(data.get("prompt", "")).strip()
    if not subject:
        return _error("请输入主体（物体）描述")
    try:
        client_id = str(uuid.uuid4())
        payload = {
            "prompt": _comfy_workflow(subject, adjective, int(time.time() * 1000) % 2**32),
            "client_id": client_id,
        }
        with httpx.Client(timeout=30) as client:
            response = client.post(f"{COMFYUI_URL}/prompt", json=payload)
            response.raise_for_status()
            prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            return _error("ComfyUI 未返回任务 ID", 502)
        filename, subfolder, image_type = _wait_for_comfy_image(prompt_id)
        with httpx.Client(timeout=60) as client:
            image_response = client.get(
                f"{COMFYUI_URL}/view",
                params={"filename": filename, "subfolder": subfolder, "type": image_type},
            )
            image_response.raise_for_status()
        output_name = f"{uuid.uuid4().hex}.png"
        (GENERATED_DIR / output_name).write_bytes(image_response.content)
        return jsonify({"success": True, "url": f"/static/generated/{output_name}"})
    except TimeoutError as exc:
        return _error(str(exc), 504)
    except Exception as exc:
        app.logger.exception("ComfyUI image generation failed")
        return _error(f"图片生成失败：{exc}", 502)


@app.post("/api/generate-3d")
def generate_3d():
    data = _json_body()
    prompt = str(data.get("prompt", "")).strip()
    image_url = str(data.get("image_url", "")).strip()

    if not prompt:
        return _error("请输入生成描述")
    if not image_url:
        return _error("请先生成图片")

    # 从本地 URL 提取文件路径
    if image_url.startswith("/static/"):
        image_path = BASE_DIR / image_url.lstrip("/")
    elif image_url.startswith("http"):
        return _error("3D 生成仅支持本地图片路径")
    else:
        image_path = BASE_DIR / "static" / image_url.strip("/")

    if not image_path.is_file():
        return _error(f"找不到图片文件：{image_path.name}", 404)

    # hunyuan3d_gen.py 脚本路径
    script_path = BASE_DIR / "hunyuan3d_gen.py"
    if not script_path.is_file():
        return _error("Hunyuan3D 脚本未找到", 500)

    try:
        output_name = f"{uuid.uuid4().hex}.glb"
        output_path = GENERATED_DIR / output_name

        cmd = [
            HUNYUAN3D_PYTHON, str(script_path),
            str(image_path), str(output_path),
            "--model", HUNYUAN3D_MODEL,
            "--steps", str(HUNYUAN3D_STEPS),
            "--octree-resolution", str(HUNYUAN3D_OCTREE_RES),
        ]
        if HUNYUAN3D_TEX:
            cmd.append("--tex")

        # 释放 ComfyUI 显存，为 Hunyuan3D 腾出空间（8GB 卡同时跑两个模型会 OOM）
        try:
            free_resp = httpx.post(
                f"{COMFYUI_URL}/free",
                json={"unload_models": True, "free_memory": True},
                timeout=10,
            )
            logging.info("ComfyUI 显存已释放: HTTP %s", free_resp.status_code)
        except Exception as exc:
            logging.warning("释放 ComfyUI 显存失败（忽略）: %s", exc)

        logging.info("Running Hunyuan3D: %s", " ".join(cmd))
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=HUNYUAN3D_TIMEOUT,
            cwd=str(BASE_DIR),
        )

        if result.returncode != 0:
            app.logger.error("Hunyuan3D stderr: %s", result.stderr)
            return _error(f"Hunyuan3D 生成失败：{result.stderr.strip().split(chr(10))[-1]}", 502)

        # 脚本成功时会 print 输出路径到 stdout
        stdout = result.stdout.strip()
        logging.info("Hunyuan3D stdout: %s", stdout)

        # 如果输出的是 .obj 而非 .glb，更新 output_name
        actual_output = stdout if stdout and Path(stdout).is_file() else str(output_path)
        if not Path(actual_output).is_file():
            return _error("3D 模型文件未生成", 502)

        # 确保前端能访问，复制到 generated 目录
        actual_path = Path(actual_output)
        if actual_path.parent != GENERATED_DIR:
            dest = GENERATED_DIR / actual_path.name
            shutil.copy2(actual_path, dest)
            actual_path = dest

        model_url = f"/static/generated/{actual_path.name}"
        # 3D 生成脚本会同时输出同名 .stl（纯几何，供 3D 打印）
        stl_path = actual_path.with_suffix('.stl')
        stl_url = f"/static/generated/{stl_path.name}" if stl_path.is_file() else None
        return jsonify({
            "success": True,
            "model_url": model_url,
            "stl_url": stl_url,
        })
    except subprocess.TimeoutExpired:
        app.logger.exception("Hunyuan3D generation timed out")
        return _error(f"Hunyuan3D 生成超时（{HUNYUAN3D_TIMEOUT} 秒）", 504)
    except Exception as exc:
        app.logger.exception("3D generation failed")
        return _error(f"3D 模型生成失败：{exc}", 502)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")), debug=False)
