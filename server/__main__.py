"""Start the API on :8000 with a Windows-safe event loop."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "server.main:app",
        host="0.0.0.0",
        port=8000,
        loop="server.winloop:loop_factory",
    )


if __name__ == "__main__":
    main()
