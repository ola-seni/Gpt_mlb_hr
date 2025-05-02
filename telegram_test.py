import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Load BOT_TOKEN and CHAT_ID from .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHAT_ID,
    "text": "✅ Telegram test: Bot is working!",
    "parse_mode": "Markdown"
}

response = requests.post(url, data=payload)
print(f"Status: {response.status_code}")
print(response.text)
