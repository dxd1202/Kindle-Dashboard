"""Build and invoke the C++ renderer, then replace the dashboard PNG."""

import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from time import perf_counter

from .config import BUILD, ROOT


def system_font(family, style):
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{family}\n%{style}\n%{file}", f"{family}:style={style}"],
            check=True, capture_output=True, text=True,
        )
        families, styles, path = result.stdout.splitlines()
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None
    if family in families.split(",") and style in styles.split(",") and Path(path).is_file():
        return path
    return None


def add_system_fonts(config):
    for weight, latin_weight in (("Regular", "Regular"), ("Bold", "SemiBold")):
        stack = [system_font("Inter", latin_weight), system_font("Sarasa Gothic SC", weight)]
        if all(stack):
            config.setdefault("dashboard_fonts", {})[weight] = stack


def build_renderer():
    started = perf_counter()
    configured = BUILD / ".dashboard-cmake-configured"
    if not configured.is_file() or not (BUILD / "CMakeCache.txt").is_file():
        subprocess.run(
            ["cmake", "-S", ROOT, "-B", BUILD, "-DCMAKE_BUILD_TYPE=Release"], check=True
        )
        configured.touch()
    subprocess.run(["cmake", "--build", BUILD, "--config", "Release", "--parallel"], check=True)
    print(f"[build] {perf_counter() - started:.2f} s", flush=True)

    renderer = BUILD / "Kindle-Dashboard"
    if os.name == "nt":
        renderer = BUILD / "Release" / "Kindle-Dashboard.exe"
        if not renderer.is_file():
            renderer = BUILD / "Kindle-Dashboard.exe"
    return renderer


def render(config, *, output=None):
    renderer = build_renderer()
    started = perf_counter()
    output = (BUILD / "output.png") if output is None else output.expanduser().absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Stage beside the destination so replacing the PNG stays atomic across filesystems.
    with TemporaryDirectory(dir=output.parent) as directory:
        render_dir = Path(directory)
        render_config = render_dir / "config.json"
        render_config.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        image = render_dir / "output.png"
        subprocess.run(
            [renderer, render_config, image],
            cwd=ROOT,
            check=True,
        )
        if not image.is_file() or image.stat().st_size == 0:
            raise RuntimeError("渲染器没有生成图片")
        image.replace(output)
    print(f"[render] {perf_counter() - started:.2f} s -> {output}", flush=True)
