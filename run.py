#!/usr/bin/env python3
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import logging
import pathlib

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).parent / ".env")

from voice_control.server import app
from voice_control.config import (
    SERVER_HOST, SERVER_PORT, AUTH_PASSWORD, TLS_CERT, TLS_KEY,
)
import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def main():
    tls = TLS_CERT and TLS_KEY and pathlib.Path(TLS_CERT).is_file() and pathlib.Path(TLS_KEY).is_file()
    proto = "https" if tls else "http"
    auth_state = "ON" if AUTH_PASSWORD else "OFF (no GO2_AUTH_PASSWORD set)"
    tls_state = "ON" if tls else "OFF (no cert)"

    print(f"╔══════════════════════════════════════════════════════════════╗")
    print(f"║     Unitree Go2 Voice Control                                ║")
    print(f"║     Dashboard: {proto}://{SERVER_HOST}:{SERVER_PORT:<5}                       ║")
    print(f"║     Auth: {auth_state:<51}║")
    print(f"║     TLS:  {tls_state:<51}║")
    print(f"╚══════════════════════════════════════════════════════════════╝")

    kwargs = dict(host=SERVER_HOST, port=SERVER_PORT, log_level="info")
    if tls:
        kwargs["ssl_certfile"] = TLS_CERT
        kwargs["ssl_keyfile"] = TLS_KEY

    uvicorn.run(app, **kwargs)


if __name__ == "__main__":
    main()
