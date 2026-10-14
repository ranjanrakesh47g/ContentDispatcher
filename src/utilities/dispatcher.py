import asyncio
import os
import random
import re
import time
import redis
import requests
from neonize.aioze.client import NewAClient
from neonize.aioze.events import ConnectedEv


class Dispatcher:
    def __init__(self, otp_ttl=20):
        self.redis = redis.Redis(decode_responses=True)
        self.otp_ttl = otp_ttl

    @staticmethod
    def number(to):
        return str(to).lstrip("+").replace(" ", "")

    def _latency(self, start, name):
        print(f"{name} latency: {time.perf_counter() - start:.2f}s")

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
        await self.send_txt_msg(f"Your code is {code}. It will expire in {self.otp_ttl} seconds", number)
        self._latency(start, "send_otp")
        return code

    async def authenticate_otp(self, number, otp):
        start = time.perf_counter()
        ok = self.redis.get(self.number(number)) == str(otp)
        self._latency(start, "authenticate_otp")
        return ok

    async def send_file(self, filepath, to):
        start = time.perf_counter()
        url = self.tinyurl(filepath)
        self._latency(start, "tinyurl")
        await self.send_txt_msg(url, to)
        self._latency(start, "send_file")


class WhatsappDispatcher(Dispatcher):
    def __init__(self, session="whatsapp_session", otp_ttl=20):
        super().__init__(otp_ttl)
        self.client = NewAClient(session)

    async def connect(self):
        ready = asyncio.Event()

        @self.client.event(ConnectedEv)
        async def on_connected(c, _event):
            ready.set()

        await self.client.connect()
        await ready.wait()

    async def send_txt_msg(self, msg, to):
        start = time.perf_counter()
        print((await self.client.send_message(self.number(to), msg)).ID)
        self._latency(start, "send_txt_msg")


class SmsDispatcher(Dispatcher):
    def __init__(self, otp_ttl=20):
        super().__init__(otp_ttl)
        self.url = os.environ.get("SMSGATE_URL", "https://api.sms-gate.app/3rdparty/v1")
        self.auth = (os.environ["SMSGATE_USERNAME"], os.environ["SMSGATE_PASSWORD"])

    async def connect(self):
        r = requests.get(f"{self.url}/health", auth=self.auth)
        r.raise_for_status()
        print(r.json())

    async def send_txt_msg(self, msg, to):
        start = time.perf_counter()
        r = requests.post(
            f"{self.url}/messages",
            auth=self.auth,
            json={"textMessage": {"text": msg}, "phoneNumbers": ["+" + self.number(to)]},
        )
        r.raise_for_status()
        print(r.json()["id"])
        self._latency(start, "send_txt_msg")
