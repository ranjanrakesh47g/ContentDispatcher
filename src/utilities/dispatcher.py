import asyncio
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
import redis
import requests
from neonize.aioze.client import NewAClient
from neonize.aioze.events import ConnectedEv

Path("logs").mkdir(exist_ok=True)
log = logging.getLogger("dispatcher")
if not log.handlers:
    handler = logging.FileHandler("logs/dispatcher.log")
    handler.terminator = "\n\n"
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


class Dispatcher:
    channel = None

    def __init__(self, otp_ttl=20):
        self.redis = redis.Redis(decode_responses=True)
        self.otp_ttl = otp_ttl

    @staticmethod
    def number(to):
        return str(to).lstrip("+").replace(" ", "")

    def _log(self, event, start=None, **fields):
        row = {
            "time": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "event": event,
            "channel": self.channel,
            **fields,
        }
        if start is not None:
            row["latency_ms"] = round((time.perf_counter() - start) * 1000, 2)
        log.info(json.dumps(row, default=str))

    def tinyurl(self, filepath):
        with open(filepath, "rb") as f:
            page = requests.post("https://tmpfiles.org/api/v1/upload", files={"file": f}).json()["data"]["url"]
        direct = re.search(r'href="(https://tmpfiles.org/dl/[^"]+)"', requests.get(page).text).group(1)
        return requests.get("https://tinyurl.com/api-create.php", params={"url": direct}).text.strip()

    async def connect(self):
        raise NotImplementedError

    async def send_txt_msg(self, msg, to):
        raise NotImplementedError

    async def send_otp(self, to):
        start = time.perf_counter()
        number = self.number(to)
        code = f"{random.randint(0, 999999):06d}"
        self.redis.set(number, code, ex=self.otp_ttl)
        msg = f"Your code is {code}. It will expire in {self.otp_ttl} seconds"
        msg_id = await self.send_txt_msg(msg, number)
        self._log("send_otp", start, to=number, id=msg_id, msg=msg)
        return code

    async def authenticate_otp(self, number, otp):
        start = time.perf_counter()
        number = self.number(number)
        ok = self.redis.get(number) == str(otp)
        self._log("authenticate_otp", start, number=number, otp=str(otp), ok=ok)
        return ok

    async def send_file(self, filepath, to):
        start = time.perf_counter()
        url = self.tinyurl(filepath)
        tinyurl_ms = round((time.perf_counter() - start) * 1000, 2)
        msg_id = await self.send_txt_msg(url, to)
        self._log("send_file", start, to=self.number(to), id=msg_id, file=filepath, url=url, msg=url, tinyurl_latency_ms=tinyurl_ms)


class WhatsappDispatcher(Dispatcher):
    channel = "whatsapp"

    def __init__(self, session="whatsapp_session", otp_ttl=20):
        super().__init__(otp_ttl)
        self.client = NewAClient(session)

    async def connect(self):
        start = time.perf_counter()
        ready = asyncio.Event()

        @self.client.event(ConnectedEv)
        async def on_connected(c, _event):
            ready.set()

        await self.client.connect()
        await ready.wait()
        self._log("connect", start)

    async def send_txt_msg(self, msg, to):
        return (await self.client.send_message(self.number(to), msg)).ID


class SmsDispatcher(Dispatcher):
    channel = "sms"

    def __init__(self, otp_ttl=20):
        super().__init__(otp_ttl)
        self.url = os.environ.get("SMSGATE_URL", "https://api.sms-gate.app/3rdparty/v1")
        self.auth = (os.environ["SMSGATE_USERNAME"], os.environ["SMSGATE_PASSWORD"])

    async def _request(self, method, path, **kwargs):
        def call():
            r = requests.request(method, f"{self.url}{path}", auth=self.auth, timeout=30, **kwargs)
            r.raise_for_status()
            return r.json()

        return await asyncio.to_thread(call)

    async def connect(self):
        start = time.perf_counter()
        health = await self._request("GET", "/health")
        self._log("connect", start, health=health)

    async def send_txt_msg(self, msg, to):
        number = self.number(to)
        body = await self._request(
            "POST",
            "/messages",
            json={"textMessage": {"text": msg}, "phoneNumbers": ["+" + number]},
        )
        return body["id"]
