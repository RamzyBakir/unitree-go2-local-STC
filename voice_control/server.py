import asyncio
import hashlib
import hmac
import json
import logging
import pathlib
import secrets
import tempfile
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, Response, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from . import config
from .audio_recorder import AudioRecorder
from .command_parser import parse_command, get_all_commands
from .keyboard_listener import KeyboardListener
from .robot_controller import RobotController
from .speech import SpeechEngine

logger = logging.getLogger(__name__)

STATIC_DIR = pathlib.Path(__file__).parent / "static"

app = FastAPI(title="Unitree Go2 Voice Control")


# ---------- Auth ----------
_AUTH_ENABLED = bool(config.AUTH_PASSWORD)
_SECRET = config.SESSION_SECRET.encode("utf-8")


def _sign(value: str) -> str:
    sig = hmac.new(_SECRET, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{value}.{sig}"


def make_session_token(username: str) -> str:
    payload = f"{username}|{int(time.time()) + config.SESSION_TTL_SECONDS}"
    return _sign(payload)


def verify_session_token(token: str) -> bool:
    if not token or "." not in token:
        return False
    payload, _, sig = token.rpartition(".")
    expected = hmac.new(_SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return False
    if "|" not in payload:
        return False
    user, _, exp = payload.partition("|")
    if not secrets.compare_digest(user, config.AUTH_USERNAME):
        return False
    try:
        return int(exp) > time.time()
    except ValueError:
        return False


# Public paths that bypass auth (login screen, its assets, healthcheck).
# style.css is shared with the dashboard but contains no secrets, so we let it through
# unauthenticated so the login page renders.
_PUBLIC_PATHS = {
    "/login", "/login.html", "/api/login", "/login.js", "/style.css", "/healthz",
}


def _is_authed(request: Request) -> bool:
    if not _AUTH_ENABLED:
        return True
    return verify_session_token(request.cookies.get(config.SESSION_COOKIE, ""))


class SessionAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not _AUTH_ENABLED:
            return await call_next(request)

        path = request.url.path
        if path in _PUBLIC_PATHS:
            return await call_next(request)

        if _is_authed(request):
            return await call_next(request)

        # Redirect HTML page loads to /login; reject API/JSON with 401.
        accepts = request.headers.get("accept", "")
        if "text/html" in accepts and request.method == "GET":
            return RedirectResponse(url=f"/login?next={path}", status_code=303)
        return JSONResponse({"error": "unauthorized"}, status_code=401)


if _AUTH_ENABLED:
    app.add_middleware(SessionAuthMiddleware)
    logger.info("Session auth ENABLED (user: %s)", config.AUTH_USERNAME)
else:
    logger.warning("Session auth DISABLED (set GO2_AUTH_PASSWORD in .env to enable)")

speech_engine = SpeechEngine()
robot = RobotController()
keyboard = None
logger.info("Keyboard disabled (not available on this system)")
recorder = AudioRecorder()

from typing import Set

_status_clients: Set[WebSocket] = set()
_pipeline_task = None


async def broadcast(msg: dict):
    disconnected = set()
    for client in _status_clients:
        try:
            await client.send_json(msg)
        except Exception:
            disconnected.add(client)
    _status_clients.difference_update(disconnected)

    # Also log to terminal for SSH visibility
    t = msg.get("type")
    if t == "transcription":
        print(f"\n🎤 Heard: \"{msg['text']}\"")
    elif t == "command_matched":
        print(f"🎯 Command: {msg['command']}")
    elif t == "command_result":
        icon = "✅" if msg["success"] else "❌"
        print(f"{icon} Result: {msg['command']} (code {msg['code']})")
    elif t == "no_match":
        print(f"⚠️  No command matched for: \"{msg.get('text', '')}\"")
    elif t == "error":
        print(f"💥 Error: {msg.get('message', '')}")


async def keyboard_pipeline():
    if keyboard is None:
        await broadcast({"type": "ready", "message": "Use web button to record voice commands"})
        return
    
    ok = keyboard.start()
    if not ok:
        logger.warning("Keyboard listener failed to start — web trigger will be available")
        await broadcast({"type": "ready", "message": "Use the web button to record voice commands"})
        return

    logger.info("Voice control pipeline started (keybind: %s)", config.KEYBIND_KEY)
    await broadcast({"type": "ready", "message": f"Press and hold {config.KEYBIND_KEY} or use web button to talk"})

    while True:
        event, _ = await keyboard.get_event()

        if event == "press":
            if recorder.is_recording:
                continue
            recorder.start()
            await broadcast({"type": "listening_started"})
            print("\n🔴 LISTENING...")

        elif event == "release":
            if not recorder.is_recording:
                continue
            filepath = recorder.stop()
            await broadcast({"type": "listening_stopped"})
            print("⏹️  Processing...")

            if not filepath:
                await broadcast({"type": "error", "message": "No audio captured"})
                continue

            try:
                text = await asyncio.to_thread(speech_engine.transcribe_file, filepath)
            except Exception as e:
                logger.error("Transcription error: %s", e)
                await broadcast({"type": "error", "message": f"Transcription failed: {e}"})
                continue

            if not text:
                await broadcast({"type": "transcription", "text": ""})
                continue

            await broadcast({"type": "transcription", "text": text})

            parsed = parse_command(text)
            if parsed is None:
                await broadcast({
                    "type": "no_match",
                    "text": text,
                    "message": f"Didn't recognize a command from: \"{text}\"",
                })
                continue

            await broadcast({
                "type": "command_matched",
                "command": parsed.display_name,
                "command_name": parsed.name,
                "text": text,
            })

            try:
                method = getattr(robot, parsed.method)
                code = await asyncio.to_thread(method, *parsed.args, **parsed.kwargs)
                await broadcast({
                    "type": "command_result",
                    "command": parsed.display_name,
                    "success": code == 0,
                    "code": code,
                })
            except Exception as e:
                logger.error("Command execution error: %s", e)
                await broadcast({
                    "type": "command_error",
                    "command": parsed.display_name,
                    "message": str(e),
                })


@app.get("/login")
async def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.post("/api/login")
async def login(req: Request):
    body = await req.json()
    user = (body.get("username") or "").strip()
    pwd = body.get("password") or ""
    ok = (
        secrets.compare_digest(user, config.AUTH_USERNAME)
        and secrets.compare_digest(pwd, config.AUTH_PASSWORD)
    )
    if not ok:
        await asyncio.sleep(0.4)  # tiny delay to slow brute-force
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)
    token = make_session_token(user)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        key=config.SESSION_COOKIE,
        value=token,
        max_age=config.SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,  # self-signed cert; can't require Secure or cookie won't survive on http fallback
    )
    return resp


@app.post("/api/logout")
async def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(config.SESSION_COOKIE)
    return resp


@app.get("/api/me")
async def me(req: Request):
    return JSONResponse({"authenticated": _is_authed(req), "username": config.AUTH_USERNAME})


@app.get("/healthz")
async def healthz():
    return JSONResponse({"ok": True})


@app.post("/api/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Accepts an audio blob from the browser, runs Whisper, then dispatches
    a command via the same flow as text-command."""
    raw = await audio.read()
    if not raw:
        return JSONResponse({"error": "Empty upload"}, status_code=400)

    suffix = pathlib.Path(audio.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw)
        path = tmp.name

    print(f"\n🎤 Got {len(raw)} bytes from browser → {path}")

    try:
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, speech_engine.transcribe_file, path)
    except Exception as e:
        logger.error("Browser-audio transcription failed: %s", e)
        await broadcast({"type": "error", "message": f"Transcription failed: {e}"})
        return JSONResponse({"error": str(e)}, status_code=500)

    if not text:
        await broadcast({"type": "transcription", "text": ""})
        return JSONResponse({"text": "", "matched": False})

    await broadcast({"type": "transcription", "text": text})

    parsed = parse_command(text)
    if parsed is None:
        await broadcast({
            "type": "no_match",
            "text": text,
            "message": f"Didn't recognize a command from: \"{text}\"",
        })
        return JSONResponse({"text": text, "matched": False})

    await broadcast({
        "type": "command_matched",
        "command": parsed.display_name,
        "command_name": parsed.name,
        "text": text,
    })

    try:
        method = getattr(robot, parsed.method)
        loop = asyncio.get_event_loop()
        code = await loop.run_in_executor(None, lambda: method(*parsed.args, **parsed.kwargs))
        await broadcast({
            "type": "command_result",
            "command": parsed.display_name,
            "success": code == 0,
            "code": code,
        })
        return JSONResponse({
            "text": text,
            "command": parsed.display_name,
            "status": "ok" if code == 0 else "error",
            "code": code,
        })
    except Exception as e:
        logger.error("Command execution error: %s", e)
        await broadcast({
            "type": "command_error",
            "command": parsed.display_name,
            "message": str(e),
        })
        return JSONResponse({"error": str(e)}, status_code=500)


@app.on_event("startup")
async def startup():
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, speech_engine.load_model)
    connected = robot.connect()
    if connected:
        logger.info("Robot connected successfully")
    else:
        logger.warning("Robot not connected — running in limited mode")

    global _pipeline_task
    _pipeline_task = asyncio.create_task(keyboard_pipeline())


@app.post("/api/record/start")
async def start_recording():
    if recorder.is_recording:
        return JSONResponse({"error": "Already recording"}, status_code=400)
    recorder.start()
    await broadcast({"type": "listening_started"})
    print("\n🔴 LISTENING...")
    return JSONResponse({"status": "recording"})


@app.post("/api/record/stop")
async def stop_recording():
    if not recorder.is_recording:
        return JSONResponse({"error": "Not recording"}, status_code=400)

    filepath = recorder.stop()
    await broadcast({"type": "listening_stopped"})
    print("⏹️  Processing...")

    if not filepath:
        await broadcast({"type": "error", "message": "No audio captured"})
        return JSONResponse({"error": "No audio captured"}, status_code=400)

    try:
        text = speech_engine.transcribe_file(filepath)
    except Exception as e:
        logger.error("Transcription error: %s", e)
        await broadcast({"type": "error", "message": f"Transcription failed: {e}"})
        return JSONResponse({"error": str(e)}, status_code=500)

    if not text:
        await broadcast({"type": "transcription", "text": ""})
        return JSONResponse({"text": ""})

    await broadcast({"type": "transcription", "text": text})

    parsed = parse_command(text)
    if parsed is None:
        await broadcast({
            "type": "no_match",
            "text": text,
            "message": f"Didn't recognize a command from: \"{text}\"",
        })
        return JSONResponse({"text": text, "matched": False})

    await broadcast({
        "type": "command_matched",
        "command": parsed.display_name,
        "command_name": parsed.name,
        "text": text,
    })

    try:
        method = getattr(robot, parsed.method)
        code = method(*parsed.args, **parsed.kwargs)
        await broadcast({
            "type": "command_result",
            "command": parsed.display_name,
            "success": code == 0,
            "code": code,
        })
        return JSONResponse({
            "command": parsed.display_name,
            "status": "ok" if code == 0 else "error",
            "code": code,
        })
    except Exception as e:
        logger.error("Command execution error: %s", e)
        await broadcast({
            "type": "command_error",
            "command": parsed.display_name,
            "message": str(e),
        })
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/text-command")
async def text_command(req: Request):
    body = await req.json()
    text = (body.get("text") or "").strip()
    if not text:
        return JSONResponse({"error": "Empty text"}, status_code=400)

    await broadcast({"type": "transcription", "text": text, "source": "manual"})

    parsed = parse_command(text)
    if parsed is None:
        await broadcast({
            "type": "no_match",
            "text": text,
            "message": f"Didn't recognize a command from: \"{text}\"",
        })
        return JSONResponse({"text": text, "matched": False})

    await broadcast({
        "type": "command_matched",
        "command": parsed.display_name,
        "command_name": parsed.name,
        "text": text,
    })

    try:
        method = getattr(robot, parsed.method)
        loop = asyncio.get_event_loop()
        code = await loop.run_in_executor(None, lambda: method(*parsed.args, **parsed.kwargs))
        await broadcast({
            "type": "command_result",
            "command": parsed.display_name,
            "success": code == 0,
            "code": code,
        })
        return JSONResponse({
            "command": parsed.display_name,
            "status": "ok" if code == 0 else "error",
            "code": code,
        })
    except Exception as e:
        logger.error("Command execution error: %s", e)
        await broadcast({
            "type": "command_error",
            "command": parsed.display_name,
            "message": str(e),
        })
        return JSONResponse({"error": str(e)}, status_code=500)


@app.on_event("shutdown")
async def shutdown():
    if keyboard:
        keyboard.stop()
    if _pipeline_task:
        _pipeline_task.cancel()
        try:
            await _pipeline_task
        except (asyncio.CancelledError, RuntimeError):
            pass


@app.get("/api/status")
async def status():
    return JSONResponse({
        "robot_connected": robot.connected,
        "mock_mode": config.MOCK_MODE,
        "whisper_model": config.WHISPER_MODEL_SIZE,
        "network_interface": config.NETWORK_INTERFACE or "default",
        "keybind": config.KEYBIND_KEY,
    })


@app.get("/api/commands")
async def list_commands():
    return JSONResponse(get_all_commands())


@app.post("/api/command/{command_name}")
async def execute_command(command_name: str):
    for cmd in get_all_commands():
        if cmd["name"] == command_name:
            parsed = parse_command(cmd["triggers"][0])
            if parsed is None:
                return JSONResponse({"error": "Command not found"}, status_code=404)
            try:
                method = getattr(robot, parsed.method)
                code = method(*parsed.args, **parsed.kwargs)
                return JSONResponse({
                    "command": parsed.display_name,
                    "status": "ok" if code == 0 else "error",
                    "code": code,
                })
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"error": "Command not found"}, status_code=404)


@app.get("/api/command/{command_name}")
async def get_command_info(command_name: str):
    for cmd in get_all_commands():
        if cmd["name"] == command_name:
            return JSONResponse(cmd)
    return JSONResponse({"error": "Command not found"}, status_code=404)


@app.websocket("/ws/status")
async def websocket_status(ws: WebSocket):
    if _AUTH_ENABLED:
        token = ws.cookies.get(config.SESSION_COOKIE, "")
        if not verify_session_token(token):
            await ws.close(code=1008)
            return
    await ws.accept()
    _status_clients.add(ws)
    logger.info("Dashboard client connected (%d total)", len(_status_clients))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _status_clients.discard(ws)
        logger.info("Dashboard client disconnected (%d remaining)", len(_status_clients))


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
