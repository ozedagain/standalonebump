import json
import os
import random
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import httpx
from httpx_ws import connect_ws, WebSocketNetworkError

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8978386709:AAHBmrZlB8puJ0dwN910Qrgjh5vZfXn6eCM"
PUMP_API_KEY = "adn4ue2ha994wy9m9hwp8gjpf9pm8vhhahpq4uk8e1bk0ukh5d4pmra18x1qct1hc5x78p36cxk30wveenj5evubb1kmex3j8rqq2nk5a8nnawhjcxc6euhf94ujpaujd116uwa9a4yku65a32y38cxx5mgvg71rpjgvh8mf5h7my1nccrprkvue5ujypa4dt8k2dj5ad0kuf8"

# Your permanent 13-digit private channel ID layout
GROUP_ID = "-1004285512360"

PUMP_BOT_URL = "https://t.me/Pump_officialBot"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BUMP_IMAGE_PATH = os.path.join(BASE_DIR, "bump.jpg")
VOLUME_IMAGE_PATH = os.path.join(BASE_DIR, "volume.png")

BOOST_OPTIONS = [
    "0.25",
    "0.35",
    "0.45",
    "0.55",
    "0.85 Mega boost",
    "1.00 Mega boost",
]
VOLUME_OPTIONS = ["1.2", "2.0", "5.1", "7.5", "10.4"]
MC_OPTIONS = ["20", "35", "48", "60", "73", "85", "97", "120"]

bot = telebot.TeleBot(BOT_TOKEN)


def truncate_address(address: str) -> str:
    """Format CA like DFqUQztL.....VfwsYFpump"""
    if not address or len(address) <= 18:
        return address
    return f"{address[:8]}.....{address[-10:]}"


def _token_fields(data):
    ticker = data.get("symbol", data.get("vbc", "UNKNOWN")).upper()
    token_name = data.get("name", "Unknown Name").upper()
    mint_address = data.get("mint", "Unknown Address")
    truncated_ca = truncate_address(mint_address)
    random_mc = random.choice(MC_OPTIONS)

    twitter = data.get("twitter")
    telegram = data.get("telegram")
    website = data.get("website")

    socials_list = []
    socials_list.append(f'<a href="{twitter}">𝕏 Twitter</a>' if twitter else "𝕏 Twitter")
    socials_list.append(f'<a href="{telegram}">✈️ Telegram</a>' if telegram else "✈️ Telegram")
    socials_list.append(f'<a href="{website}">🌐 Website</a>' if website else "🌐 Website")
    socials_text = "  ·  ".join(socials_list)

    return ticker, token_name, truncated_ca, random_mc, socials_text


# ==========================================
# TEXT FORMATTING LOGIC
# ==========================================
def format_bump_message(data):
    ticker, token_name, truncated_ca, random_mc, socials_text = _token_fields(data)
    random_boost = random.choice(BOOST_OPTIONS)

    return (
        f"🚀 <b>NEW BUMP ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💊 <b>${ticker}</b>\n\n"
        f"📍 <b>Address</b>\n"
        f"<code>{truncated_ca}</code>\n\n"
        f"⚡ <b>Boost</b>   →  <code>{random_boost}</code>\n"
        f"🏷 <b>Name</b>    →  {token_name}\n"
        f"💰 <b>MC</b>      →  ${random_mc}k\n\n"
        f"🔗 <b>Socials</b>\n"
        f"{socials_text}"
    )


def format_volume_message(data):
    ticker, token_name, truncated_ca, random_mc, socials_text = _token_fields(data)
    random_volume = random.choice(VOLUME_OPTIONS)

    return (
        f"📊 <b>NEW VOLUME ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💊 <b>${ticker}</b>\n\n"
        f"📍 <b>Address</b>\n"
        f"<code>{truncated_ca}</code>\n\n"
        f"📈 <b>Volume</b>  →  <code>{random_volume}</code>\n"
        f"🏷 <b>Name</b>    →  {token_name}\n"
        f"💰 <b>MC</b>      →  ${random_mc}k\n\n"
        f"🔗 <b>Socials</b>\n"
        f"{socials_text}"
    )


def create_inline_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="💊 Start PumpFun Bot", url=PUMP_BOT_URL))
    return markup


def send_alert(image_path, caption):
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Alert image not found: {image_path}")

    reply_markup = create_inline_keyboard()
    with open(image_path, "rb") as photo:
        bot.send_photo(
            chat_id=GROUP_ID,
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )


def post_token_alerts(data):
    """Post bump + volume alerts using local directory images."""
    send_alert(BUMP_IMAGE_PATH, format_bump_message(data))
    print(f"[Alert] Bump alert posted ({os.path.basename(BUMP_IMAGE_PATH)}).")

    time.sleep(1)
    send_alert(VOLUME_IMAGE_PATH, format_volume_message(data))
    print(f"[Alert] Volume alert posted ({os.path.basename(VOLUME_IMAGE_PATH)}).")


# ==========================================
# AUTOMATED WEBSOCKET LOOP
# ==========================================
def listen_to_stream(ws):
    print("[Status] Connected to PumpPortal WebSocket. Subscribing to token creation stream...")
    payload = {"method": "subscribeNewToken"}
    ws.send_text(json.dumps(payload))

    while True:
        try:
            message = ws.receive_text()
            data = json.loads(message)

            if data.get("txType") == "create" or "mint" in data:
                print(f"[Alert] New token: {data.get('name')} ({data.get('mint')}). Applying 3s delay...")
                time.sleep(3)
                post_token_alerts(data)

        except json.JSONDecodeError:
            continue
        except Exception as e:
            print(f"[Error] Failed to parse message or send channel post: {e}")
            break


def run_websocket():
    ws_url = f"wss://pumpportal.fun/api/data?api-key={PUMP_API_KEY}"

    while True:
        try:
            print("[Status] Attempting to connect to PumpPortal using HTTPX...")
            with httpx.Client() as client:
                with connect_ws(ws_url, client) as ws:
                    listen_to_stream(ws)
        except WebSocketNetworkError as ne:
            print(f"[Error] Network drop: {ne}")
        except Exception as e:
            print(f"[Error] Connection loop failure: {e}")

        print("[Status] Reconnecting to WebSocket in 5 seconds...")
        time.sleep(5)


# ==========================================
# RENDER ANTI-SLEEP + ALERT WEBHOOK
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[HTTP] {self.address_string()} - {format % args}")

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/bump.jpg", "/volume.png"):
            filename = self.path.lstrip("/")
            image_path = os.path.join(BASE_DIR, filename)
            if not os.path.isfile(image_path):
                self.send_error(404, f"{filename} not found")
                return

            content_type = "image/jpeg" if filename.endswith(".jpg") else "image/png"
            with open(image_path, "rb") as image_file:
                data = image_file.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is Awake!")

    def do_POST(self):
        if self.path not in ("/webhook", "/alert"):
            self._send_json(404, {"ok": False, "error": "Not found"})
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw.decode("utf-8") or "{}")
            post_token_alerts(data)
            self._send_json(200, {"ok": True, "message": "Bump and volume alerts posted"})
        except Exception as e:
            print(f"[Webhook] Failed to post alerts: {e}")
            self._send_json(500, {"ok": False, "error": str(e)})


def run_health_server():
    server = HTTPServer(("0.0.0.0", 10000), HealthCheckHandler)
    print("[System] Health + webhook server active on port 10000")
    print(f"[System] Images dir: {BASE_DIR}")
    print(f"[System] Bump image: {BUMP_IMAGE_PATH} (exists={os.path.isfile(BUMP_IMAGE_PATH)})")
    print(f"[System] Volume image: {VOLUME_IMAGE_PATH} (exists={os.path.isfile(VOLUME_IMAGE_PATH)})")
    server.serve_forever()


def keep_alive_loop():
    while True:
        time.sleep(600)
        try:
            urllib.request.urlopen("http://localhost:10000", timeout=5)
            print("[System] Keep-alive ping sent to self successfully.")
        except Exception as e:
            print(f"[System] Internal ping skipped: {e}")


# ==========================================
# RUNTIME INITIALIZATION
# ==========================================
if __name__ == "__main__":
    for path in (BUMP_IMAGE_PATH, VOLUME_IMAGE_PATH):
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Required image missing in bot directory: {path}")

    # 1. Start Render health check + webhook server thread
    threading.Thread(target=run_health_server, daemon=True).start()

    # 2. Start internal self-ping loop thread
    threading.Thread(target=keep_alive_loop, daemon=True).start()

    # 3. Immediately kick-off the PumpPortal streaming connection thread
    print("[System] Launching automated streaming engine...")
    threading.Thread(target=run_websocket, daemon=True).start()

    # Keep main thread alive safely since bot handlers aren't polling anymore
    while True:
        time.sleep(1)
