#!/usr/bin/env python3
"""SpliceGAIP desktop/web launcher.

Starts the local web server and opens the UI in the default browser, so a
double-click on the packaged exe gives a usable graphical interface:

    python serve_ui.py                 # pick a free port, open the browser
    python serve_ui.py --port 8800
    python serve_ui.py --no-browser    # serve only (e.g. remote/SSH use)
"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# When frozen, PyInstaller already put the bundle on sys.path; __file__ there
# points inside the temporary archive and must not be used as a source root.
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

try:  # the file names the launcher recognises (kept in one place)
    from splicegaip.llm.envfile import CONFIG_FILE_NAMES as _CONFIG_NAMES
except Exception:  # noqa: BLE001 - import happens before the app is ready
    _CONFIG_NAMES = (".env", "配置大模型.env")


def _load_local_env() -> list[Path]:
    """Load every configuration file sitting next to the exe / sources.

    Recognises both ``.env`` and ``配置大模型.env`` (see
    :mod:`splicegaip.llm.envfile`): a key found in either file is used, and
    existing environment variables still win so a launcher script keeps
    precedence. Returns the files actually read, for the startup banner.
    """
    try:
        from splicegaip.llm.envfile import load_env_values

        return load_env_values()
    except Exception:  # noqa: BLE001 - never block startup on config loading
        return []


def _write_env_templates() -> list[Path]:
    """Drop fill-in templates next to the exe for every recognised name.

    Writes ``.env.example`` *and* ``配置大模型.env.example`` so it is obvious
    either file name works; existing files are never overwritten and any
    failure (read-only directory) is tolerated.
    """
    if getattr(sys, "frozen", False):
        folder = Path(sys.executable).resolve().parent
        source = Path(getattr(sys, "_MEIPASS", ".")) / ".env.example"
        if not source.is_file():
            source = Path(__file__).resolve().parent / ".env.example"
    else:
        folder = Path(__file__).resolve().parent
        source = folder / ".env.example"
    if not source.is_file():
        return []
    try:
        content = source.read_text(encoding="utf-8")
    except OSError:
        return []
    written: list[Path] = []
    for name in (".env.example", "配置大模型.env.example"):
        target = folder / name
        if target.is_file():
            continue
        try:
            target.write_text(content, encoding="utf-8")
            written.append(target)
        except OSError:
            continue
    return written


def _free_port(start: int, attempts: int = 40) -> int:
    """Return the first free TCP port at or after ``start``."""
    for offset in range(attempts):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"No free port found in range {start}-{start + attempts - 1}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the SpliceGAIP web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="0 = auto-pick a free port")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser")
    args = parser.parse_args()

    port = args.port or _free_port(8800)

    env_files = _load_local_env()
    templates = _write_env_templates()
    llm_ready = bool(os.environ.get("MODEL_API_KEY") and os.environ.get("MODEL_API_BASE_URL"))
    model_name = os.environ.get("MODEL_NAME", "")

    import uvicorn

    from splicegaip.api.app import create_app

    app = create_app()
    url = f"http://{args.host}:{port}/"

    print("=" * 62)
    print("  SpliceGAIP — AI 驱动可变剪接分析平台")
    print(f"  地址: {url}")
    if llm_ready:
        print(f"  大模型: 已接入 {model_name or '(未指定 MODEL_NAME)'} · AI 解读已启用")
        if env_files:
            print(f"  配置文件: {', '.join(str(p) for p in env_files)}")
        try:
            from splicegaip.config import load_settings

            from splicegaip.llm.client import describe_llm_mode

            print(f"          端点详情: {describe_llm_mode(load_settings())}")
        except Exception:  # noqa: BLE001 - banner must never break startup
            pass
    else:
        print("  大模型: 未配置 · 当前为离线确定性模式（结果与接入模型时一致）")
        print("          打开网页后到「AI 解读 → 模型配置」粘贴密钥即可启用（无需重启），")
        print(f"          或编辑下列任一文件后重启：{'、'.join(_CONFIG_NAMES)}")
        if env_files:
            print(f"          已读取配置: {', '.join(str(p) for p in env_files)}")
            print("          检测到 MODEL_API_KEY 为空 —— 请把密钥写进上述任一文件")
        elif templates:
            print(f"  已生成配置模板: {'、'.join(str(p) for p in templates)}")
            print("          把模板复制为 .env（同目录）并填入密钥，重启后即可启用 AI 解读")
    print("  浏览器已自动打开；关闭本窗口即可停止服务。")
    print("=" * 62, flush=True)

    if not args.no_browser:
        # Open once the server is actually accepting connections.
        threading.Thread(target=_open_when_ready, args=(url,), daemon=True).start()

    uvicorn.run(app, host=args.host, port=port, log_level="warning")
    return 0


def _open_when_ready(url: str, timeout: float = 60.0) -> None:
    """Poll the health endpoint, then open the browser."""
    import urllib.request

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url + "api/health", timeout=2) as response:
                if response.status == 200:
                    break
        except Exception:  # noqa: BLE001 - server not up yet
            time.sleep(0.4)
    else:
        print(f"  服务已启动，但未能自动打开浏览器，请手动访问: {url}", flush=True)
        return

    try:
        opened = webbrowser.open(url)
    except Exception:  # noqa: BLE001 - headless / no default browser
        opened = False
    if opened:
        print(f"  浏览器已打开: {url}", flush=True)
    else:
        print(f"  未能自动打开浏览器，请手动访问: {url}", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
