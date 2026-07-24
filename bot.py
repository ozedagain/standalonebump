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
    reply_markup = create_inline_keyboard()
    with open(image_path, "rb") as photo:
        bot.send_photo(
            chat_id=GROUP_ID,
            photo=photo,
            caption=caption,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )


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

                send_alert(BUMP_IMAGE_PATH, format_bump_message(data))
                print("[Alert] Bump alert posted.")

                time.sleep(1)
                send_alert(VOLUME_IMAGE_PATH, format_volume_message(data))
                print("[Alert] Volume alert posted.")

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
# RENDER ANTI-SLEEP LOOPHOLE INFRASTRUCTURE
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is Awake!")

def run_health_server():
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    print("[System] Anti-sleep local web server active on port 10000")
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
    # 1. Start Render health check server thread
    threading.Thread(target=run_health_server, daemon=True).start()

    # 2. Start internal self-ping loop thread
    threading.Thread(target=keep_alive_loop, daemon=True).start()

    # 3. Immediately kick-off the PumpPortal streaming connection thread
    print("[System] Launching automated streaming engine...")
    threading.Thread(target=run_websocket, daemon=True).start()

    # Keep main thread alive safely since bot handlers aren't polling anymore
    while True:
        time.sleep(1)
