import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("Telegram sozlamalari topilmadi")

# Telegram botini tekshirish
r = requests.get(
    f"https://api.telegram.org/bot{TOKEN}/getMe"
)
r.raise_for_status()

print("Telegram bot ulandi!")

# Sinov xabari
r = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,
        "text": "Хадислар боти ишга туширишга тайёр!"
    }
)
r.raise_for_status()

print("Telegram xabari yuborildi!")
