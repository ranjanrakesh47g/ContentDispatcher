# Content Dispatcher

Content Dispatcher sends an OTP, verifies it, and delivers a file link (pdf/image) over WhatsApp and SMS.

WhatsApp messages are sent with Neonize, using a linked device session. SMS messages are sent with SMSGate through the Android application on the sender phone. Generated OTPs are stored in Redis for the expiration-time (in seconds) specified in `config.yml`. A file is uploaded to a temporary host, shortened with TinyURL, and the resulting link is sent as a text message via WhatApp/SMS channel.

## Service comparison


| Service | Base plan | Channels and allowance | Remarks |
| --- | --- | --- | --- |
| Neonize | • Free, open source. No subscription required. | • WhatsApp only, sent from the linked sender account.<br>• No vendor quota. | • Uses a QR-linked device session.<br>• Not the official WhatsApp Business API. |
| SMSGate | • Free, open source. No subscription required. | • SMS and MMS from the sender phone's SIM.<br>• Volume follows the carrier plan, not an SMSGate quota. | • Requires the Android app to be installed to stay online.<br>• The app is not available on the Play Store, and needs installation of the official APK from the project releases.<br>• A personal SIM may reject OTP-style text, hence might need a commercial SIM card. |
| Twilio | • 30-day trial, no card required.<br>• The minimum balance to upgrade is $20, and it is pay-as-you-go.<br>• US SMS starts at $0.0083 per segment plus carrier fees.<br>• WhatsApp starts at $0.005 per message plus Meta fees.<br>• A phone number starts at $1.15 per month. | • SMS, MMS, RCS, WhatsApp, email, and voice.<br>• Trial account inclusions: 100 SMS, 100 WhatsApp messages, 3,000 emails, and 75 voice minutes. | • Official APIs.<br>• Trial use is limited to verified recipients and expires after 30 days.<br>• Trial messages use Twilio's predefined templates.<br>• Custom message text and file attachments are allowed only in the upgraded account. |




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
  
3. Set up SMSGate on the sender phone, then create a `.env` file in the project root.

    a. Download **SMS Gateway for Android** from the official releases page: https://github.com/capcom6/android-sms-gateway/releases. The app is not on the Play Store. Use the standard APK, not the build marked insecure.
   
    b. If Play Protect blocks the install, open Google Play Store → profile → Play Protect → settings, turn off **Scan apps with Play Protect**, install the APK, then turn the scan back on.
   
    c. Open the app, turn on **Cloud server**, and copy the username and password from the home screen into a `.env` file in the project root: `SMSGATE_USERNAME` and `SMSGATE_PASSWORD`

5. Run the API from the project root.
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

