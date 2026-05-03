import asyncio
import json
import logging
import pathlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .audio_recorder import AudioRecorder
from .command_parser import parse_command, get_all_commands
from .keyboard_listener import KeyboardListener
from .robot_controller import RobotController
from .speech import SpeechEngine

logger = logging.getLogger(__name__)

STATIC_DIR = pathlib.Path(__file__).parent / "static"

app = FastAPI(title="Unitree Go2 Voice Control")

speech_engine = SpeechEngine()
robot = RobotController()
keyboard = KeyboardListener(config.KEYBIND_KEY)
recorder = AudioRecorder()

_status_clients: set[WebSocket] = set()
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
    ok = keyboard.start()
    if not ok:
        logger.error("Keyboard listener failed to start — voice control disabled")
        await broadcast({"type": "error", "message": "Keyboard listener failed to start. Check permissions and USB keyboard."})
        return

    logger.info("Keyboard pipeline started (keybind: %s)", config.KEYBIND_KEY)
    await broadcast({"type": "ready", "message": f"Press and hold {config.KEYBIND_KEY} to talk"})

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


@app.on_event("startup")
async def startup():
    speech_engine.load_model()
    connected = robot.connect()
    if connected:
        logger.info("Robot connected successfully")
    else:
        logger.warning("Robot not connected — running in limited mode")

    global _pipeline_task
    _pipeline_task = asyncio.create_task(keyboard_pipeline())


@app.on_event("shutdown")
async def shutdown():
    keyboard.stop()
    if _pipeline_task:
        _pipeline_task.cancel()
        try:
            await _pipeline_task
        except asyncio.CancelledError:
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


@app.websocket("/ws/status")
async def websocket_status(ws: WebSocket):
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
