"""One-command Linq demo: ngrok + webhook subscribe + uvicorn.

From the repo root (ngrok authtoken already configured):

    python -m server.dev

Ctrl+C stops ngrok and the server.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from shutil import which

import httpx

from server.envload import linq_api_key, load_plusone_env
from server.subscribe_linq import subscribe

ROOT = Path(__file__).resolve().parents[1]
NGROK_API = "http://127.0.0.1:4040/api/tunnels"


def find_ngrok() -> Path | None:
    override = os.environ.get("NGROK_PATH", "").strip()
    if override:
        path = Path(override)
        return path if path.is_file() else None
    found = which("ngrok")
    if found:
        return Path(found)
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    candidates = [
        local / "Microsoft/WinGet/Links/ngrok.exe",
        local / "Microsoft/WinGet/Packages/Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe/ngrok.exe",
        Path(r"C:\Program Files\ngrok\ngrok.exe"),
        Path.home() / "ngrok.exe",
        ROOT / "ngrok.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _ensure_linq_from() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    text = env_path.read_text(encoding="utf-8")
    if "LINQ_FROM=" in text:
        return
    with env_path.open("a", encoding="utf-8") as handle:
        handle.write("\nLINQ_FROM=+19492783794\n")


def wait_for_ngrok(timeout: float = 45.0) -> str | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = httpx.get(NGROK_API, timeout=1.5)
            for tunnel in response.json().get("tunnels") or []:
                url = str(tunnel.get("public_url") or "")
                if url.startswith("https://"):
                    return url.rstrip("/")
        except httpx.HTTPError:
            pass
        time.sleep(0.4)
    return None


def _free_port(port: int) -> None:
    """Stop whatever is already listening so uvicorn can bind (Windows)."""
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"],
            text=True,
            errors="ignore",
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return
    pids: set[int] = set()
    needle = f":{port}"
    for line in out.splitlines():
        if needle not in line or "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if not parts:
            continue
        try:
            pids.add(int(parts[-1]))
        except ValueError:
            continue
    me = os.getpid()
    for pid in pids:
        if pid in (0, me):
            continue
        print(f"Port {port} busy (pid {pid}); stopping it so the new server can start.")
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            check=False,
        )
    if pids:
        time.sleep(0.6)


def _lan_ip() -> str:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        return str(ip)
    except OSError:
        return ""


def main() -> int:
    os.chdir(ROOT)
    load_plusone_env()
    if not linq_api_key():
        print("Add LINQ=... to C:\\Projects\\PlusOne\\.env first.", file=sys.stderr)
        return 1
    _ensure_linq_from()

    ngrok_bin = find_ngrok()
    if ngrok_bin is None:
        print(
            "Can't find ngrok.exe. Install with: winget install ngrok.Ngrok\n"
            "Then close this terminal, open a new one, and run python -m server.dev again.\n"
            "Or set NGROK_PATH to the full path of ngrok.exe.",
            file=sys.stderr,
        )
        return 1
    print(f"Using ngrok at {ngrok_bin}")

    ngrok_proc = None
    uvicorn_proc = None
    log_path = ROOT / "server" / "ngrok.dev.log"
    tunnel = wait_for_ngrok(timeout=1.5)
    if tunnel:
        print("Reusing an ngrok tunnel that is already running.")
    else:
        print("Starting ngrok http 8000…")
        log_file = log_path.open("w", encoding="utf-8")
        ngrok_proc = subprocess.Popen(
            [str(ngrok_bin), "http", "8000", "--log=stdout", "--log-format=logfmt"],
            cwd=ROOT,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        tunnel = wait_for_ngrok()
        if not tunnel:
            print(
                "ngrok did not publish an https URL. The authtoken is saved, but "
                "this process could not talk to ngrok's local API.",
                file=sys.stderr,
            )
            if ngrok_proc.poll() is not None:
                print(f"ngrok exited with code {ngrok_proc.returncode}. Last log:", file=sys.stderr)
            if log_path.exists():
                print(log_path.read_text(encoding="utf-8")[-1500:], file=sys.stderr)
            if ngrok_proc:
                ngrok_proc.terminate()
            return 1

    print(f"Tunnel ready: {tunnel}")
    print(f"Webhook path: {tunnel}/linq/webhook?version=2026-02-03")
    if subscribe(tunnel, write_env=True) != 0:
        if ngrok_proc:
            ngrok_proc.terminate()
        return 1

    load_plusone_env()
    _free_port(8000)
    print("Starting Plus One on http://0.0.0.0:8000 …")
    uvicorn_proc = subprocess.Popen(
        [sys.executable, "-m", "server"],
        cwd=ROOT,
    )

    def _stop(*_args) -> None:
        if uvicorn_proc and uvicorn_proc.poll() is None:
            uvicorn_proc.terminate()
        if ngrok_proc and ngrok_proc.poll() is None:
            ngrok_proc.terminate()

    signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    print()
    print("Ready. Leave this window open.")
    lan = _lan_ip()
    if lan:
        print(f"Expo phones: host {lan}:8000  (not localhost)")
    print("Text +1 (949) 278-3794  →  I can't do more than $150")
    print("Inspector: http://127.0.0.1:4040")
    print("Events:    http://127.0.0.1:8000/rooms/demo/events")
    print()
    return uvicorn_proc.wait()


if __name__ == "__main__":
    raise SystemExit(main())
