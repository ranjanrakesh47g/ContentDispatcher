import time
from contextlib import asynccontextmanager
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse as jsonify
from src.utilities import SmsDispatcher, WhatsappDispatcher

load_dotenv()

dispatchers = {
    "whatsapp": WhatsappDispatcher(),
    "sms": SmsDispatcher(),
}


@asynccontextmanager
async def lifespan(_app):
    for dispatcher in dispatchers.values():
        await dispatcher.connect()
    yield


app = FastAPI(lifespan=lifespan)


def latency(start):
    return f"{round((time.perf_counter() - start) * 1000)} ms"


@app.get("/health_check")
async def health_check():
    start = time.perf_counter()
    return jsonify({"ok": True, "latency": latency(start)})


@app.post("/send_otp")
async def send_otp(channel: Literal["whatsapp", "sms"], to: str):
    start = time.perf_counter()
    await dispatchers[channel].send_otp(to)
    return jsonify({"ok": True, "latency": latency(start)})


@app.post("/authenticate_otp")
async def authenticate_otp(channel: Literal["whatsapp", "sms"], number: str, otp: str):
    start = time.perf_counter()
    ok = await dispatchers[channel].authenticate_otp(number, otp)
    return jsonify({"ok": ok, "latency": latency(start)})


@app.post("/send_file")
async def send_file(channel: Literal["whatsapp", "sms"], to: str, filepath: str):
    start = time.perf_counter()
    await dispatchers[channel].send_file(filepath, to)
    return jsonify({"ok": True, "latency": latency(start)})
