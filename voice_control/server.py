import asyncio
import json
import logging
import pathlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .command_parser import parse_command, get_all_commands
from .robot_controller import RobotController
from .speech import SpeechEngine

logger = logging.getLogger(__name__)

STATIC_DIR = pathlib.Path(__file__).parent / "static"

app = FastAPI(title="Unitree Go2 Voice Control")

speech_engine = SpeechEngine()
robot = RobotController()


@app.on_event("startup")
async def startup():
    speech_engine.load_model()
    connected = robot.connect()
    if connected:
        logger.info("Robot connected successfully")
    else:
        logger.warning("Robot not connected — running in limited mode")


@app.get("/api/status")
async def status():
    return JSONResponse(
        {
            "robot_connected": robot.connected,
            "mock_mode": config.MOCK_MODE,
            "whisper_model": config.WHISPER_MODEL_SIZE,
            "network_interface": config.NETWORK_INTERFACE or "default",
        }
    )


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
                return JSONResponse(
                    {
                        "command": parsed.display_name,
                        "status": "ok" if code == 0 else "error",
                        "code": code,
                    }
                )
            except Exception as e:
                return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"error": "Command not found"}, status_code=404)


@app.websocket("/ws/audio")
async def websocket_audio(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            audio_bytes = await ws.receive_bytes()
            if not audio_bytes:
                continue

            try:
                text = await asyncio.to_thread(speech_engine.transcribe, audio_bytes)
            except Exception as e:
                logger.error("Transcription error: %s", e)
                await ws.send_json(
                    {"type": "error", "message": f"Transcription failed: {e}"}
                )
                continue

            if not text:
                await ws.send_json({"type": "transcription", "text": ""})
                continue

            await ws.send_json({"type": "transcription", "text": text})

            parsed = parse_command(text)
            if parsed is None:
                await ws.send_json(
                    {
                        "type": "no_match",
                        "text": text,
                        "message": f'Didn\'t recognize a command from: "{text}"',
                    }
                )
                continue

            await ws.send_json(
                {
                    "type": "command_matched",
                    "command": parsed.display_name,
                    "text": text,
                }
            )

            try:
                method = getattr(robot, parsed.method)
                code = await asyncio.to_thread(method, *parsed.args, **parsed.kwargs)
                await ws.send_json(
                    {
                        "type": "command_result",
                        "command": parsed.display_name,
                        "success": code == 0,
                        "code": code,
                    }
                )
            except Exception as e:
                logger.error("Command execution error: %s", e)
                await ws.send_json(
                    {
                        "type": "command_error",
                        "command": parsed.display_name,
                        "message": str(e),
                    }
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
