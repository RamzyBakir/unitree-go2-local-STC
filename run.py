#!/usr/bin/env python3
import sys
import logging
from voice_control.server import app
from voice_control.config import SERVER_HOST, SERVER_PORT
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def main():
    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║     Unitree Go2 Voice Control                                ║")
    print(f"║     Dashboard: http://{SERVER_HOST}:{SERVER_PORT:>5}                          ║")
    print(f"╚══════════════════════════════════════════════════════════════╝")
    print("")
    print("Press Ctrl+C to stop")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, log_level="info")


if __name__ == "__main__":
    main()
