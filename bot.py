import json
import random
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import httpx
from httpx_ws import connect_ws, WebSocketSession, WebSocketNetworkError

# ==========================================
# CONFIGURATION PLACEHOLDERS
# ==========================================
BOT_TOKEN = "8978386709:AAHBmrZlB8puJ0dwN910Qrgjh5vZfXn6eCM"
PUMP_API_KEY = "adn4ue2ha994wy9m9hwp8gjpf9pm8vhhahpq4uk8e1bk0ukh5d4pmra18x1qct1hc5x78p36cxk30wveenj5evubb1kmex3j8rqq2nk5a8nnawhjcxc6euhf94ujpaujd116uwa9a4yku65a32y38cxx5mgvg71rpjgvh8mf5h7my1nccrprkvue5ujypa4dt8k2dj5ad0kuf8"
GROUP_ID = "-1003911675310"

# Direct verified CDN image URL path
IMAGE_URL = "https://phototourl.com" 

# Global state trackers to manage running services safely
bot = telebot.TeleBot(BOT_TOKEN)
stream_active = False
stream_lock = threading.Lock()
current_ws = None  # Tracks the active connection to close it on stop


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Handles the /start command. Boots up the pump.fun websocket stream.
    """
    global stream_active
    
    with stream_lock:
        if not stream_active:
            bot.reply_to(message, "⚡ <b>PumpPortal stream triggered!</b> Live token updates will now stream instantly into this chat layout.", parse_mode="HTML")
            print("[System] /start command detected. Spawning background WebSocket thread now...")
            stream_active = True
            ws_thread = threading.Thread(target=run_websocket)
            ws_thread.daemon = True
            ws_thread.start()
        else:
            bot.reply_to(message, "ℹ️ <b>Stream is already running</b> and posting updates.", parse_mode="HTML")


@bot.message_handler(commands=['stop'])
def stop_stream(message):
    """
    Handles the /stop command. Safely breaks the active loop and closes the WebSocket connection.
    """
    global stream_active, current_ws
    
    with stream_lock:
        if stream_active:
            bot.reply_to(message, "🛑 <b>Stopping stream...</b> Live token updates have been paused.", parse_mode="HTML")
            print("[System] /stop command detected. Terminating active data stream...")
            stream_active = False
            
            # Force close the socket connection immediately if it exists
            if current_ws:
                try:
                    current_ws.close()
                except Exception:
                    pass
                current_ws = None
        else:
            bot.reply_to(message, "ℹ️ <b>Stream is already stopped.</b> Type /start to activate it again.", parse_mode="HTML")


def format_message(data):
    ticker = data.get("vbc", data.get("symbol", "UNKNOWN")).upper()
    token_name = data.get("name", "Unknown Name").upper()
    mint_address = data.get("mint", "Unknown Address")

    package_tiers = [
        ("0.2", "2 Hours"), ("0.4", "3 Hours"), ("0.6", "4 Hours"),
        ("1.5", "6 Hours"), ("2.5", "12 Hours")
    ]
    random_package, random_duration = random.choice(package_tiers)

    mc_options = ["60", "73", "53", "79", "64", "90", "145", "67"]
    v60_options = ["123", "245", "89", "312", "174", "420", "95", "210"]
    random_mc = random.choice(mc_options)
    random_v60 = random.choice(v60_options)

    twitter = data.get("twitter")
    telegram = data.get("telegram")
    website = data.get("website")

    socials_list = []
    socials_list.append(f'<a href="{website}"><b>𝗪𝗲𝗯</b></a>' if website else "<b>𝗪𝗲𝗯</b>")
    socials_list.append(f'<a href="{telegram}"><b>𝗧𝗴</b></a>' if telegram else "<b>𝗧𝗴</b>")
    socials_list.append(f'<a href="{twitter}"><b>𝗫</b></a>' if twitter else "<b>𝗫</b>")
    socials_text = " | ".join(socials_list)

    message = (
        f"📣 | <b>BUMP BOOST!</b>\n\n\n"
        f"✅ | <b>${ticker}</b> has just gotten bumps.\n\n"
        f"🔷 | <b>Contract Address:</b>\n"
        f"<code>{mint_address}</code>\n\n"
        f"®️ | <b>Name:</b> {token_name}\n"
        f"©️ | <b>Ticker:</b> ${ticker}\n"
        f"📈 | <b>MC:</b> ${random_mc}k\n"
        f"📈 | <b>V 60min:</b> ${random_v60}\n"
        f"📣 | <b>Socials:</b> {socials_text}\n\n"
        f"⭐️ | <b>Package:</b> {random_package}\n"
        f"⚙️ | <b>Duration:</b> {random_duration}"
    )
    return message, mint_address


def create_inline_keyboard(mint_address):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="⚡ Quick Buy (PumpPortal)", url=f"https://pump.fun{mint_address}"))
    markup.add(InlineKeyboardButton(text="📈 Trade on Photon", url=f"https://tinyastro.io{mint_address}"))
    return markup


# ==========================================
# HTTPX WEBSOCKET STREAM LOGIC
# ==========================================
def listen_to_stream(ws: WebSocketSession):
    global stream_active
    print("[Status] Connected to PumpPortal WebSocket. Subscribing to token creation stream...")
    payload = {"method": "subscribeNewToken"}
    ws.send_text(json.dumps(payload))

    while stream_active: # Will break out of loop cleanly if stream_active changes to False
        try:
            message = ws.receive_text()
            data = json.loads(message)

            if data.get("txType") == "create" or "mint" in data:
                print(f"[Alert] New token detected: {data.get('name')} ({data.get('mint')}). Applying 3-second sleep timer...")
                
                time.sleep(3)
                
                # Check again after sleep to ensure user didn't hit stop during those 3 seconds
                if not stream_active:
                    break
                    
                formatted_caption, mint_address = format_message(data)
                reply_markup = create_inline_keyboard(mint_address)
                
                bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=IMAGE_URL,
                    caption=formatted_caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
                    
        except json.JSONDecodeError:
            continue
        except Exception as e:
            print(f"[Error] Failed to process message or send telegram alert: {e}")
            break


def run_websocket():
    global stream_active, current_ws
    ws_url = f"wss://pumpportal.fun/api/data?api-key={PUMP_API_KEY}"
    
    while stream_active:
        try:
            print("[Status] Attempting to connect to PumpPortal using HTTPX...")
            with connect_ws(ws_url) as ws:
                current_ws = ws # Save globally so stop handler can reach it
                listen_to_stream(ws)
        except WebSocketNetworkError as ne:
            print(f"[Error] Network exception dropped connection: {ne}")
        except Exception as e:
            print(f"[Error] Connection loop failure: {e}")
        
        # Only try to reconnect if the user didn't intentionally stop the bot
        if stream_active:
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
# INITIALIZATION & EXECUTION
# ==========================================
if __name__ == "__main__":
    print("[System] Initializing bot services...")

    # Start Render's sleep prevention layers immediately
    threading.Thread(target=run_health_server, daemon=True).start()
    threading.Thread(target=keep_alive_loop, daemon=True).start()

    print("[System] Starting TeleBot long polling runner...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=5)
        except Exception as e:
            print(f"[Error] Telegram polling crash caught: {e}")
            print("[Status] Restarting polling loop in 5 seconds...")
            time.sleep(5)
