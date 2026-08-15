#!/usr/bin/env python3
"""Hunyuan3D 2.0 standalone wrapper — called by Flask as a subprocess.

Usage:
    python hunyuan3d_gen.py <input_image> <output_path> [--tex] [--steps 30]

Outputs a GLB file. Prints the output path on stdout on success.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import torch
from PIL import Image


def main():
    parser = argparse.ArgumentParser(description="Hunyuan3D 2.0 Image-to-3D")
    parser.add_argument("input", type=str, help="Path to input RGB/RGBA image")
    parser.add_argument("output", type=str, help="Path for output GLB file")
    parser.add_argument("--tex", action="store_true", help="Enable texture generation")
    parser.add_argument("--steps", type=int, default=30, help="Inference steps (default 30)")
    parser.add_argument("--octree-resolution", type=int, default=256, help="Mesh resolution (default 256)")
    parser.add_argument("--model", type=str, default="tencent/Hunyuan3D-2mini", help="Model path or HuggingFace ID")
    parser.add_argument("--use-safetensors", action="store_true", help="Use .safetensors weights (default: .ckpt)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.is_file():
        print(f"ERROR: input image not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[hunyuan3d] device={device}, model={args.model}, steps={args.steps}", file=sys.stderr)

    # --- Load image & remove background ---
    t0 = time.time()
    image = Image.open(input_path).convert("RGB")
    from hy3dgen.rembg import BackgroundRemover
    rembg = BackgroundRemover()
    image = rembg(image)
    print(f"[hunyuan3d] image loaded ({time.time() - t0:.1f}s)", file=sys.stderr)

    # --- Shape generation ---
    t0 = time.time()
    from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline

    print(f"[hunyuan3d] loading shape model...", file=sys.stderr)
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        args.model,
        subfolder='hunyuan3d-dit-v2-mini',
        use_safetensors=args.use_safetensors)
    print(f"[hunyuan3d] shape model loaded ({time.time() - t0:.1f}s)", file=sys.stderr)

    t0 = time.time()
    print(f"[hunyuan3d] generating shape...", file=sys.stderr)
    mesh = pipeline(
        image=image,
        num_inference_steps=args.steps,
        octree_resolution=args.octree_resolution,
    )[0]
    print(f"[hunyuan3d] shape done in {time.time() - t0:.1f}s, vertices={len(mesh.vertices)}", file=sys.stderr)

    # --- Texture generation (optional) ---
    if args.tex:
        t0 = time.time()
        from hy3dgen.texgen import Hunyuan3DPaintPipeline

        print(f"[hunyuan3d] loading texture model...", file=sys.stderr)
        tex_pipeline = Hunyuan3DPaintPipeline.from_pretrained(args.model)
        print(f"[hunyuan3d] applying texture...", file=sys.stderr)
        mesh = tex_pipeline(mesh, image=image)
        print(f"[hunyuan3d] texture done in {time.time() - t0:.1f}s", file=sys.stderr)

    # --- Export ---
    t0 = time.time()
    # Trimesh 5.x compatibility: export as GLB
    if hasattr(mesh, 'export'):
        mesh.export(str(output_path))
        # 同时导出 STL（纯几何，不含纹理，供 3D 打印/切割使用）
        stl_path = output_path.with_suffix('.stl')
        mesh.export(str(stl_path))
        print(f"[hunyuan3d] exported STL to {stl_path}", file=sys.stderr)
    else:
        # fallback: write OBJ
        obj_path = str(output_path).replace('.glb', '.obj')
        with open(obj_path, 'w') as f:
            mesh.export(file_type='obj')
        print(f"[hunyuan3d] exported OBJ to {obj_path}", file=sys.stderr)

    print(f"[hunyuan3d] exported to {output_path} ({time.time() - t0:.1f}s)", file=sys.stderr)
    print(str(output_path))  # <-- Flask reads this line


if __name__ == "__main__":
    main()
