# Local AI Background Remover — CLI Edition

A local, offline background removal tool designed as a **seamless executor** for AI agentic workflows. Processes one image per invocation and returns a pure JSON response — no UI, no cloud, no API keys.

---

## Features

- Removes image backgrounds entirely on-device using the `rembg` ONNX model
- Auto-detects hardware and uses the fastest available accelerator (CoreML on Apple Silicon, CUDA on Linux/Windows with NVIDIA GPU, DirectML on Windows with AMD/Intel GPU, CPU everywhere else)
- All output is **pure JSON to stdout** — machine-readable by design
- Output is always saved as PNG to preserve transparency
- Zero external network calls after first model download

---

## Minimum Specifications

| Component | Minimum | Recommended |
|---|---|---|
| **OS** | Windows 10 64-bit, macOS 12, Ubuntu 20.04 | Windows 11, macOS 13+, Ubuntu 22.04 |
| **Python** | 3.10 | 3.11+ |
| **CPU** | Any x86_64 or arm64 (2 cores) | 4+ cores |
| **RAM** | 4 GB | 8 GB |
| **Disk** | 500 MB free | 1 GB free |
| **GPU** | Not required | NVIDIA (CUDA), Apple Silicon (CoreML), AMD/Intel (DirectML on Windows) |
| **Internet** | Required once (model download ~170 MB) | — |

> **RAM note:** The `u2net` model loads ~170 MB into RAM. On a 4 GB machine with other applications open, processing large images (4K+) may be slow. 8 GB is comfortable for typical photo sizes (up to ~20 MP).

---

## Installation

**1. Clone or copy the project folder.**

**2. Create and activate a virtual environment:**

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows (Command Prompt)
python -m venv .venv
.venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> **Windows PowerShell note:** If you get an execution policy error, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**3. Install dependencies — pick your platform:**

**macOS / Linux (CPU only — works everywhere):**
```bash
pip install "rembg[cpu]" pillow
```

**Apple Silicon (M1/M2/M3/M4) — enables CoreML / Metal acceleration:**
```bash
pip install "rembg[cpu]" pillow
pip uninstall onnxruntime -y
pip install onnxruntime-silicon
```

**Linux with NVIDIA GPU — enables CUDA acceleration:**
```bash
pip install "rembg[gpu]" pillow
```

**Windows (CPU only):**
```batch
pip install rembg pillow
```

**Windows with NVIDIA GPU — enables CUDA acceleration:**
```batch
pip install rembg pillow
pip uninstall onnxruntime -y
pip install onnxruntime-gpu
```

**Windows with AMD or Intel GPU — enables DirectML acceleration:**
```batch
pip install rembg pillow
pip uninstall onnxruntime -y
pip install onnxruntime-directml
```

---

## Usage

```bash
# macOS / Linux
python remove_bg.py -i <input_image> -o <output_path>

# Windows
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

# Absolute paths (macOS / Linux)
python remove_bg.py -i /home/agyan/raw/product.jpg -o /home/agyan/results/product.png

# Absolute paths (Windows)
python remove_bg.py -i "C:\Users\agyan\Pictures\product.jpg" -o "C:\Users\agyan\results\product.png"
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

| Value | Platform | Accelerator |
|---|---|---|
| `coreml` | macOS arm64 | Apple Neural Engine / Metal |
| `cuda` | Linux, Windows | NVIDIA GPU via CUDA |
| `directml` | Windows | AMD / Intel GPU via DirectML |
| `cpu` | All platforms | CPU fallback |

---

## Notes

- The first run downloads the model weights (~170 MB for `u2net`) to `~/.u2net/` (macOS/Linux) or `C:\Users\<you>\.u2net\` (Windows). Subsequent runs are fully offline.
- The output directory is created automatically if it does not exist.
- The output is always PNG regardless of the extension you specify in `--output`.
- All stderr output from ONNX Runtime is suppressed so stdout remains clean JSON.
- On Windows, use quoted paths when they contain spaces: `"C:\My Photos\image.jpg"`.
