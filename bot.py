import json
import random
import time
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from httpx_ws import connect_ws, WebSocketSession, WebSocketNetworkError

# ==========================================
# CONFIGURATION
# ==========================================
BOT_TOKEN = "8978386709:AAHBmrZlB8puJ0dwN910Qrgjh5vZfXn6eCM"
PUMP_API_KEY = "adn4ue2ha994wy9m9hwp8gjpf9pm8vhhahpq4uk8e1bk0ukh5d4pmra18x1qct1hc5x78p36cxk30wveenj5evubb1kmex3j8rqq2nk5a8nnawhjcxc6euhf94ujpaujd116uwa9a4yku65a32y38cxx5mgvg71rpjgvh8mf5h7my1nccrprkvue5ujypa4dt8k2dj5ad0kuf8"
GROUP_ID = "-1003911675310"

# Hosted Image Link (Using your raw GitHub image link so Koyeb doesn't need a local file)
IMAGE_URL = "https://github.com"

# Initialize the Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN)

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
    socials_list.append(f'<a href="{website}">𝗪𝗲𝗯</a>' if website else "𝗪𝗲𝗯")
    socials_list.append(f'<a href="{telegram}">𝗧𝗴</a>' if telegram else "𝗧𝗴")
    socials_list.append(f'<a href="{twitter}">𝗫</a>' if twitter else "𝗫")
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

def listen_to_stream(ws: WebSocketSession):
    print("[Status] Connected to PumpPortal WebSocket. Subscribing...")
    payload = {"method": "subscribeNewToken"}
    ws.send_text(json.dumps(payload))

    while True:
        try:
            message = ws.receive_text()
            data = json.loads(message)

            if data.get("txType") == "create" or "mint" in data:
                print(f"[Alert] New token: {data.get('name')}")
                formatted_caption, mint_address = format_message(data)
                reply_markup = create_inline_keyboard(mint_address)
                
                # Send using the online GitHub image URL directly
                bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=IMAGE_URL,
                    caption=formatted_caption,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
        except Exception as e:
            print(f"[Error] Failed to process message: {e}")
            break

def run_websocket():
    ws_url = f"wss://pumpportal.fun/api/data?api-key={PUMP_API_KEY}"
    while True:
        try:
            print("[Status] Connecting to PumpPortal...")
            with connect_ws(ws_url) as ws:
                listen_to_stream(ws)
        except WebSocketNetworkError as ne:
            print(f"[Error] Network issue: {ne}")
        except Exception as e:
            print(f"[Error] Loop failure: {e}")
        
        print("[Status] Reconnecting in 5 seconds...")
        time.sleep(5)

if __name__ == "__main__":
    run_websocket()
