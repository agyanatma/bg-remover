# CLAUDE.md — Agent Integration Guide: Local Background Remover

This file is the authoritative integration reference for AI agents and orchestrators that invoke `remove_bg.py` as a tool.

---

## What This Tool Does

Removes the background from a single image file and saves the result as a PNG with a transparent background. Runs entirely locally — no network calls, no external APIs.

---

## Invocation

```
<python_executable> remove_bg.py -i <input_path> -o <output_path> [--model <model_name>]
```

**Always use the venv Python, not the system Python:**

```bash
# macOS / Linux
/path/to/bg-remover/.venv/bin/python remove_bg.py -i image.jpg -o result.png

# Windows
C:\path\to\bg-remover\.venv\Scripts\python.exe remove_bg.py -i image.jpg -o result.png
```

---

## Parameters

| Parameter | Required | Type | Description |
|---|---|---|---|
| `-i` / `--input` | Yes | string (path) | Absolute or relative path to the source image |
| `-o` / `--output` | Yes | string (path) | Destination path. Extension is **always overridden to `.png`** |
| `--model` | No | enum | AI model variant (default: `u2net`) |

### `--model` Values

| Value | Use When |
|---|---|
| `u2net` | Default. General purpose, fastest (~900ms on M3). Use for products, objects, anything non-human. |
| `u2net_human_seg` | Subject is a person or portrait. |
| `isnet-general-use` | Fine edges matter (hair, fur, transparent objects). Slower (~2-3s). |

**Decision rule for agents:** default to `u2net`. Override to `u2net_human_seg` if you know the subject is a person. Override to `isnet-general-use` only when quality is explicitly required and latency is acceptable.

---

## Response Contract

The tool writes **one JSON object to stdout** and exits. Nothing else is written to stdout. Stderr is suppressed.

### Success (exit code 0)

```json
{
  "status": "success",
  "input_file": "/abs/path/to/source.jpg",
  "output_file": "/abs/path/to/result.png",
  "hardware_backend": "coreml",
  "inference_time_ms": 889,
  "file_size_kb": 764.36
}
```

### Error (exit code 1)

```json
{
  "status": "error",
  "message": "<human-readable reason>",
  "input_file": "/abs/path/to/source.jpg"
}
```

**Parsing rule:** check `status` first. If `"success"`, the output PNG is ready at `output_file`. If `"error"`, surface `message` to the user or log it — do not attempt to read `output_file`.

---

## Field Reference

| Field | Type | Always Present | Description |
|---|---|---|---|
| `status` | `"success"` \| `"error"` | Yes | Outcome |
| `input_file` | string (abs path) | Yes | Resolved absolute path of the input |
| `output_file` | string (abs path) | On success | Absolute path of the saved PNG |
| `hardware_backend` | `"coreml"` \| `"cuda"` \| `"rocm"` \| `"directml"` \| `"cpu"` | On success | Accelerator used for inference |
| `inference_time_ms` | integer (ms) | On success | Wall-clock time of the `remove()` call only |
| `file_size_kb` | float (KB) | On success | Size of the output PNG file |
| `message` | string | On error | Error description |

---

## Hardware Backend Behavior

The tool auto-detects the optimal backend — no configuration needed.

| Platform | Detected Backend | Notes |
|---|---|---|
| macOS arm64 (Apple Silicon) | `coreml` | Requires `onnxruntime-silicon` installed in venv |
| Linux / Windows with NVIDIA GPU | `cuda` | Requires `onnxruntime-gpu` installed in venv |
| Linux with AMD GPU | `rocm` | Requires `onnxruntime-rocm` + ROCm 6.x host drivers |
| Windows with AMD / Intel GPU | `directml` | Requires `onnxruntime-directml` installed in venv |
| Any other platform | `cpu` | Always available, slowest; tune with `OMP_NUM_THREADS` |

---

## Constraints and Guarantees

- **One image per invocation.** The tool is stateless; invoke it once per image.
- **Output is always PNG.** The alpha (transparency) channel requires PNG. Any extension in `--output` is silently replaced with `.png`.
- **Output directory is auto-created.** You do not need to pre-create the destination directory.
- **Input path must exist and be a regular file.** Symlinks to files are fine. Directories are not.
- **Supported input formats:** JPEG, PNG, WEBP, BMP, TIFF — any format readable by Pillow.
- **First-run model download:** On first use, the model weights (~170MB for `u2net`) are downloaded to `~/.u2net/`. Subsequent runs are fully offline. If the environment has no internet access, pre-seed `~/.u2net/` manually.
- **Stderr is fully suppressed.** Do not parse stderr. All actionable information is in the JSON on stdout.

---

## Error Conditions

| `message` pattern | Root Cause | Resolution |
|---|---|---|
| `Input file not found: …` | `--input` path does not exist | Verify the path before invoking |
| `Input path is not a regular file: …` | `--input` is a directory or special file | Pass a file path, not a directory |
| `Missing dependency: …` | `rembg` or `pillow` not installed in venv | Run `pip install "rembg[cpu]" pillow` in the venv |
| Any other message | Inference failure (corrupt image, OOM, model error) | Log `message` and treat as unrecoverable for this image |

---

## Example Agent Call (Python)

```python
import subprocess
import json

result = subprocess.run(
    [".venv/bin/python", "remove_bg.py", "-i", input_path, "-o", output_path],
    capture_output=True,
    text=True,
    cwd="/path/to/bg-remover",
)

response = json.loads(result.stdout)

if response["status"] == "success":
    print(f"Saved to: {response['output_file']} ({response['file_size_kb']} KB)")
    print(f"Took {response['inference_time_ms']}ms on {response['hardware_backend']}")
else:
    print(f"Failed: {response['message']}")
```

---

## Project Structure

```
bg-remover/
├── remove_bg.py      # Main CLI script — only file you need to invoke
├── requirements.txt  # Pip dependencies
├── README.md         # Human-facing documentation
└── CLAUDE.md         # This file — agent integration reference
```
