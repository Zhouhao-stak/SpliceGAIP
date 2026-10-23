"""Windowed desktop launcher for the local SpliceGAIP application."""

from __future__ import annotations

import threading
import time
import urllib.request

import uvicorn
import webview

from serve_ui import _free_port, _load_local_env, _write_env_templates
from splicegaip.api.app import create_app


def main() -> int:
    _load_local_env()
    _write_env_templates()
    port = _free_port(8800)
    url = f"http://127.0.0.1:{port}/"
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error"))
    worker = threading.Thread(target=server.run, name="splicegaip-api", daemon=True)
    worker.start()

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if not worker.is_alive():
            raise RuntimeError("本地分析服务未能启动。")
        try:
            with urllib.request.urlopen(url + "api/health", timeout=1) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(0.25)
    else:
        server.should_exit = True
        raise RuntimeError("本地分析服务启动超时。")

    try:
        webview.create_window("SpliceGAIP", url, width=1440, height=900, min_size=(1000, 650), background_color="#061923")
        webview.start(gui="edgechromium", private_mode=False)
    finally:
        server.should_exit = True
        worker.join(timeout=5)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # A windowed executable has no console in which to show startup errors.
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, str(error), "SpliceGAIP 启动失败", 0x10)
        raise
