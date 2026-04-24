# Local AI Background Remover — CLI Edition

A local, offline background removal tool designed as a **seamless executor** for AI agentic workflows. Processes one image per invocation and returns a pure JSON response — no UI, no cloud, no API keys.

---

## Features

- Removes image backgrounds entirely on-device using the `rembg` ONNX model
- Auto-detects hardware and uses the fastest available accelerator (CoreML on Apple Silicon, CUDA on Linux/Windows with NVIDIA GPU, CPU everywhere else)
- All output is **pure JSON to stdout** — machine-readable by design
- Output is always saved as PNG to preserve transparency
- Zero external network calls after first model download

---

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| OS | macOS (Apple Silicon or Intel), Linux |
| Disk space | ~180 MB for the default `u2net` model (downloaded once on first run) |

---

## Installation

**1. Clone or copy the project folder.**

**2. Create and activate a virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

**3. Install dependencies:**

```bash
pip install "rembg[cpu]" pillow
```

**Apple Silicon (M1/M2/M3/M4) — recommended for best performance:**

```bash
pip install "rembg[cpu]" pillow
pip uninstall onnxruntime -y
pip install onnxruntime-silicon   # enables CoreML / Metal acceleration
```

**Linux with NVIDIA GPU:**

```bash
pip install "rembg[gpu]" pillow   # pulls onnxruntime-gpu automatically
```

---

## Usage

```bash
python remove_bg.py -i <input_image> -o <output_path>
```

### Arguments

| Argument | Short | Required | Description |
|---|---|---|---|
| `--input` | `-i` | Yes | Path to source image (JPEG, PNG, WEBP, BMP) |
| `--output` | `-o` | Yes | Destination path for the result (always saved as `.png`) |
| `--model` | | No | AI model to use (see table below, default: `u2net`) |

### Model Options

| Model | Speed | Quality | Best For |
|---|---|---|---|
| `u2net` | Fast (~900ms) | Good | General purpose — **default** |
| `u2net_human_seg` | Fast | Good | People and portraits only |
| `isnet-general-use` | Slower (~2-3s) | High | Fine detail, hair, complex edges |

### Examples

```bash
# Basic usage
python remove_bg.py -i photo.jpg -o photo_nobg.png

# High-quality model for a portrait
python remove_bg.py -i portrait.jpg -o portrait_nobg.png --model u2net_human_seg

# Absolute paths
python remove_bg.py -i /Users/agyan/raw/product.jpg -o /Users/agyan/results/product.png
```

---

## Output Format

### Success

```json
{
  "status": "success",
  "input_file": "/Users/agyan/images/photo.jpg",
  "output_file": "/Users/agyan/images/photo_nobg.png",
  "hardware_backend": "coreml",
  "inference_time_ms": 889,
  "file_size_kb": 764.36
}
```

### Error

```json
{
  "status": "error",
  "message": "Input file not found: /bad/path/photo.jpg",
  "input_file": "/bad/path/photo.jpg"
}
```

Exit code is `0` on success, `1` on any error.

### `hardware_backend` Values

| Value | Meaning |
|---|---|
| `coreml` | Apple Silicon — CoreML / Metal (fastest on macOS arm64) |
| `cuda` | NVIDIA GPU via CUDA |
| `cpu` | CPU fallback (all platforms) |

---

## Notes

- The first run downloads the model weights (~170MB for `u2net`) to `~/.u2net/`. Subsequent runs are fully offline.
- The output directory is created automatically if it does not exist.
- The output is always PNG regardless of the extension you specify in `--output`.
- All stderr output from ONNX Runtime is suppressed so stdout remains clean JSON.
