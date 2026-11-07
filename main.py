import os
import requests

# Telegram bot tokenini tekshirish
telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
groq_key = os.getenv("GROQ_API_KEY")

if not telegram_token:
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi")

if not groq_key:
    raise ValueError("GROQ_API_KEY topilmadi")

# Telegram API tekshiruvi
url = f"https://api.telegram.org/bot{telegram_token}/getMe"
response = requests.get(url)
response.raise_for_status()

print("Telegram bot muvaffaqiyatli ulandi!")

# Groq API tekshiruvi
url = "https://api.groq.com/openai/v1/models"
response = requests.get(
    url,
    headers={"Authorization": f"Bearer {groq_key}"}
)
response.raise_for_status()

print("Groq AI muvaffaqiyatli ulandi!")
