
import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GROQ_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN or not CHAT_ID or not GROQ_KEY:
    raise ValueError("Telegram yoki Groq sozlamalari topilmadi")

# 1. Abu Dawud 107-hadisni olish
urls = [
    "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-abudawud/107.min.json",
    "https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/ara-abudawud/107.json"
]

data = None

for url in urls:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        break
    except requests.RequestException:
        continue

if data is None:
    raise ValueError("Hadis manbasidan ma'lumot olinmadi")

# 2. Hadis matnini ajratib olish
record = None

if isinstance(data, dict):
    if isinstance(data.get("hadith"), dict):
        record = data["hadith"]
    elif isinstance(data.get("hadiths"), list):
        record = next(
            (h for h in data["hadiths"]
             if str(h.get("hadithnumber")) == "107"),
            None
        )
    elif "text" in data:
        record = data

if not record or not record.get("text"):
    raise ValueError("Hadis matni topilmadi")

arabic = record["text"]

translation_response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "openai/gpt-oss-20b",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Quyidagi arabcha hadisni o'zbek tiliga "
                    "kirill yozuvida to'liq tarjima qil. "
                    "Hech qanday izoh qo'shma. "
                    "Faqat tarjimani yoz:\n\n" + arabic
                )
            }
        ],
        "reasoning_effort": "low",
        "include_reasoning": False,
        "temperature": 0.2,
        "max_completion_tokens": 2048
    },
    timeout=60
)

translation_response.raise_for_status()

translation = (
    translation_response.json()["choices"][0]
    ["message"]["content"] or ""
).strip()

if not translation:
    raise ValueError("Groq tarjimani bo'sh qaytardi!")


# 4. Telegramga yuborish
message = (
    "📖 СУНАН АБУ ДОВУД\n"
    "Ҳадис № 107\n\n"
    f"{arabic}\n\n"
    f"🇺🇿 {translation}\n\n"
    "Манба: Абу Довуд"
)

telegram_response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    json={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=30
)

telegram_response.raise_for_status()

print("Hadis muvaffaqiyatli yuborildi!")

