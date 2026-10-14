# Content Dispatcher

Content Dispatcher sends an OTP, verifies it, and delivers a file link (pdf/image) over WhatsApp and SMS.

WhatsApp messages are sent with Neonize, using a linked device session. SMS messages are sent with SMSGate through the Android application on the sender phone. Generated OTPs are stored in Redis for the expiration-time (in seconds) specified in `config.yml`. A file is uploaded to a temporary host, shortened with TinyURL, and the resulting link is sent as a text message via WhatApp/SMS channel.

## APIs

The server listens on `http://127.0.0.1:8000`. Each response includes `latency` in milliseconds.


| Method | Path                | Parameters                         |
| ------ | ------------------- | ---------------------------------- |
| GET    | `/health_check`     | None                               |
| POST   | `/send_otp`         | Query: `channel`, `to`             |
| POST   | `/authenticate_otp` | Query: `channel`, `number`, `otp`  |
| POST   | `/send_file`        | Form data: `channel`, `to`, `file` |


- `channel` is `whatsapp` or `sms`.
- Recipient numbers (`to` or `number` field) must include the country code, for example `+916207xxx854`.
- `POST /send_otp` generates the OTP, sends it and returns a JSON `{"ok": true, "latency": "123 ms"}`. The OTP itself is not included in the response.
- `POST /authenticate_otp` returns `{"ok": true}` or `{"ok": false}`, together with `latency`.
- `POST /send_file` accepts a multipart form. In Postman, set the body type to form-data, add `channel` and `to` as text fields, and add `file` as `file` field.



## Setup

1. Create the virtual environment and install dependencies.
  ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
  ```
2. Start Redis before the application.
  ```bash
    sudo docker run -d --name otp-redis -p 6379:6379 redis:7
  ```
    If that container already exists, start it with `sudo docker start otp-redis`.
3. For SMS, create a `.env` file in the project root.
  ```
    SMSGATE_USERNAME=
    SMSGATE_PASSWORD=
  ```
4. Run the API from the project root.
  ```bash
    python -m src.api.main
  ```
5. On the first WhatsApp login, a QR code is printed in the terminal. Scan it from the sender phone with WhatsApp → Linked devices. The login is saved in `whatsapp_session`. Later runs reuse that file and do not request a new scan.



## Docker

1. Build the image from the project root.
  ```bash
    sudo docker build -t content-dispatcher .
  ```
2. Start Redis before the application.
  ```bash
    sudo docker run -d --name otp-redis -p 6379:6379 redis:7
  ```
    If that container already exists, start it with `sudo docker start otp-redis`.
3. Start the container from the project root. `-it` allocates a terminal so the WhatsApp QR code can be displayed on the first login. `--network host` lets the container reach Redis on the host, and `--env-file .env` supplies the SMSGate credentials.
  ```bash
    sudo docker run --rm -it --network host --env-file .env content-dispatcher
  ```

