#!/usr/bin/env python3
import argparse
import contextlib
import io
import json
import os
import platform
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _suppress_stderr():
    """Redirect stderr at the file-descriptor level.

    sys.stderr = io.StringIO() only silences Python-level writes.
    ONNX Runtime and its C extensions write directly to fd 2, so we must
    duplicate the real fd, point fd 2 at /dev/null, then restore after.
    """
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    saved_fd = os.dup(2)
    os.dup2(devnull_fd, 2)
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stderr = old_stderr
        os.dup2(saved_fd, 2)
        os.close(saved_fd)
        os.close(devnull_fd)


def _emit(payload: dict, exit_code: int = 0) -> None:
    """Write a JSON payload to stdout and exit. The single exit point."""
    print(json.dumps(payload, indent=2))
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# Hardware detection — YOUR CONTRIBUTION GOES HERE
# ---------------------------------------------------------------------------

def detect_hardware_backend() -> tuple[str, list[str]]:
    """Return (backend_label, onnx_providers_list) for the current machine.

    backend_label  — human/machine-readable string that ends up in the JSON
                     response and (later) the analytics DB.
    onnx_providers — ordered list passed directly to rembg's new_session().
                     ONNX Runtime tries providers left-to-right and falls
                     back automatically, so order matters.

    Platforms to handle:
      - macOS arm64  → CoreML is fastest; fall back to CPU
      - Linux/other  → probe for CUDA; fall back to CPU

    TODO: implement this function.
    The body below is a safe CPU-only placeholder so the script runs while
    you fill in the real logic (5-10 lines).
    """
    machine = platform.machine().lower()
    system = platform.system().lower()

    if system == "darwin" and machine == "arm64":
        return "coreml", ["CoreMLExecutionProvider", "CPUExecutionProvider"]

    try:
        import onnxruntime as ort
        available = ort.get_available_providers()
        if "CUDAExecutionProvider" in available:
            return "cuda", ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if "ROCMExecutionProvider" in available:
            return "rocm", ["ROCMExecutionProvider", "CPUExecutionProvider"]
        if "DmlExecutionProvider" in available:
            return "directml", ["DmlExecutionProvider", "CPUExecutionProvider"]
    except Exception:
        pass

    return "cpu", ["CPUExecutionProvider"]


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def _resolve_paths(raw_input: str, raw_output: str) -> tuple[Path, Path]:
    input_path = Path(raw_input).resolve()
    output_path = Path(raw_output).resolve().with_suffix(".png")
    return input_path, output_path


def _validate_input(input_path: Path) -> None:
    if not input_path.exists():
        _emit({
            "status": "error",
            "message": f"Input file not found: {input_path}",
            "input_file": str(input_path),
        }, exit_code=1)
    if not input_path.is_file():
        _emit({
            "status": "error",
            "message": f"Input path is not a regular file: {input_path}",
            "input_file": str(input_path),
        }, exit_code=1)


def _run_inference(
    input_path: Path,
    output_path: Path,
    model_name: str,
    providers: list[str],
) -> int:
    """Remove background and save PNG. Returns inference time in ms."""
    try:
        from rembg import new_session, remove
        from PIL import Image
    except ImportError as exc:
        _emit({
            "status": "error",
            "message": f"Missing dependency: {exc}. Run: pip install rembg[cpu] pillow",
            "input_file": str(input_path),
        }, exit_code=1)

    try:
        with _suppress_stderr():
            session = new_session(model_name=model_name, providers=providers)
            raw_bytes = input_path.read_bytes()

            t0 = time.perf_counter()
            result_bytes = remove(raw_bytes, session=session)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            img = Image.open(io.BytesIO(result_bytes))
            img.save(output_path, "PNG")

        return elapsed_ms

    except Exception as exc:
        _emit({
            "status": "error",
            "message": str(exc),
            "input_file": str(input_path),
        }, exit_code=1)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="remove_bg",
        description="Local AI background remover — outputs pure JSON for agentic workflows.",
    )
    parser.add_argument("-i", "--input", required=True, metavar="PATH",
                        help="Path to input image (JPEG, PNG, WEBP, …)")
    parser.add_argument("-o", "--output", required=True, metavar="PATH",
                        help="Destination path for the result (always saved as PNG)")
    parser.add_argument("--model", default="u2net",
                        choices=["u2net", "u2net_human_seg", "isnet-general-use"],
                        help="rembg model (default: u2net — fastest general-purpose)")

    args = parser.parse_args()

    input_path, output_path = _resolve_paths(args.input, args.output)
    _validate_input(input_path)

    backend_label, providers = detect_hardware_backend()
    elapsed_ms = _run_inference(input_path, output_path, args.model, providers)

    file_size_kb = round(output_path.stat().st_size / 1024, 2)

    _emit({
        "status": "success",
        "input_file": str(input_path),
        "output_file": str(output_path),
        "hardware_backend": backend_label,
        "inference_time_ms": elapsed_ms,
        "file_size_kb": file_size_kb,
    })


if __name__ == "__main__":
    main()
