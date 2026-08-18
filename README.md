# 3D Maker

这是一个"文字生成 2D 图片，再由图片生成 3D 模型"的 Flask + Three.js 工程。

当前图片生成使用本地 ComfyUI + SDXL，3D 生成使用本地 TripoSR。

## 1. 安装 ComfyUI 和 SDXL

先在本机安装 ComfyUI，并下载 SDXL Base 模型。将模型文件放到 ComfyUI 的 `models/checkpoints` 目录，例如：

```text
ComfyUI/models/checkpoints/sd_xl_base_1.0.safetensors
```

启动 ComfyUI，默认地址为：

```text
http://127.0.0.1:8188
```

启动后可以打开 `http://127.0.0.1:8188` 检查是否正常。

## 2. 配置后端

进入 `platform/backend`，复制 `.env.example` 为 `.env`。

重点配置：

```env
COMFYUI_URL=http://127.0.0.1:8188
COMFYUI_CHECKPOINT=sd_xl_base_1.0.safetensors
COMFYUI_WIDTH=1024
COMFYUI_HEIGHT=1024
TRIPOSR_DEVICE=cuda
TRIPOSR_MC_RESOLUTION=256
```

TripoSR 模型首次运行时会自动从 HuggingFace 下载权重（`stabilityai/TripoSR`），也可配置本地路径。

## 3. 安装 Python 依赖并启动

```powershell
cd platform
py -3.10 -m venv seed3D_env
seed3D_env\Scripts\python.exe -m pip install -r backend\requirements.txt
cd backend
..\seed3D_env\Scripts\python.exe app.py
```

浏览器打开：

```text
http://localhost:5000/
```

## 4. 接口

- `GET /api/health`：检查 Flask、ComfyUI 和 TripoSR 状态。
- `POST /api/generate-image`：提交文字，后端调用 ComfyUI SDXL 并返回本地图片 URL。
- `POST /api/generate-3d`：提交图片 URL，后端调用本地 TripoSR 推理并返回 OBJ 模型文件。

## 5. 当前图片工作流

后端自动提交标准 ComfyUI 工作流：

```text
CheckpointLoaderSimple
        ↓
CLIPTextEncode（正向提示词）
CLIPTextEncode（负向提示词）
        ↓
KSampler → VAEDecode → SaveImage
```

默认会自动加入适合 3D 的约束：单一物体、完整轮廓、三分之四视角、浅色纯背景、无文字、无人物、无遮挡。

## 6. 当前 3D 工作流

后端使用本地 TripoSR 进行单图 3D 重建：

```text
输入图片 → rembg 去背景 → resize_foreground 调整
    ↓
TripoSR 前向推理 → Marching Cubes 提取 Mesh
    ↓
导出 OBJ → 返回本地文件 URL
```

模型默认使用 `stabilityai/TripoSR`，在 CUDA GPU 上推理，通常几秒到十几秒即可完成。

## 7. 本地翻译模型（离线中译英）

中文提示词通过本地 `Helsinki-NLP/opus-mt-zh-en` 模型离线翻译，不依赖任何外部翻译 API，
避免网络波动导致语义错乱（如「椅子」生成「摩托车」）。

模型权重未入库（约 555MB），首次部署需手动下载到 `platform/backend/models/opus-mt-zh-en/`：

```bash
cd platform/backend/models
mkdir -p opus-mt-zh-en && cd opus-mt-zh-en
# 通过国内镜像下载（国内环境推荐；海外可把 hf-mirror.com 换成 huggingface.co）
BASE="https://hf-mirror.com/Helsinki-NLP/opus-mt-zh-en/resolve/main"
for f in config.json generation_config.json tokenizer_config.json vocab.json source.spm target.spm pytorch_model.bin; do
  curl -sL "$BASE/$f" -o "$f"
done
```

原模型是旧格式 `pytorch_model.bin`，需转成 `safetensors` 才能被新版 transformers + torch<2.6 安全加载：

```bash
cd platform/backend
seed3D_env\Scripts\python.exe -c "import torch; from safetensors.torch import save_file; s=torch.load('models/opus-mt-zh-en/pytorch_model.bin', map_location='cpu', weights_only=True); save_file({k:v.clone() for k,v in s.items()}, 'models/opus-mt-zh-en/model.safetensors')"
rm models/opus-mt-zh-en/pytorch_model.bin
```

下载并转换完成后，`models/opus-mt-zh-en/` 下应包含：`config.json`、`model.safetensors`、`source.spm`、`target.spm`、`vocab.json`、`tokenizer_config.json`、`generation_config.json`。

