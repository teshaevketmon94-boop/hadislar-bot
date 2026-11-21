
import os
import json
import requests
import subprocess

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GROQ_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN or not CHAT_ID or not GROQ_KEY:
    raise ValueError("Telegram yoki Groq sozlamalari topilmadi")

# 1. Hadislar navbati
books = [
    ("ara-bukhari", "САҲИҲ АЛ-БУХОРИЙ"),
    ("ara-muslim", "САҲИҲ МУСЛИМ"),
    ("ara-abudawud", "СУНАН АБУ ДОВУД"),
    ("ara-tirmidhi", "ЖОМЕЪ АТ-ТЕРМИЗИЙ"),
    ("ara-nasai", "СУНАН АН-НАСОИЙ"),
    ("ara-ibnmajah", "СУНАН ИБН МОЖА")
]

# 2. Navbatni o'qish
STATE_FILE = "state.json"

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)
else:
    state = {"book_index": 0, "hadith_number": 107}

book_index = state["book_index"]
hadith_number = state["hadith_number"]

if book_index < 0 or book_index >= len(books):
    raise ValueError("Kitob navbati noto'g'ri")

edition, book_name = books[book_index]

print(f"Kitob: {book_name}, hadis: {hadith_number}")

# 3. Hadisni manbadan olish
base_url = (
    f"https://cdn.jsdelivr.net/gh/fawazahmed0/"
    f"hadith-api@1/editions/{edition}/{hadith_number}"
)

data = None

for url in [base_url + ".min.json", base_url + ".json"]:
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        break
    except requests.RequestException:
        continue

if data is None:
    raise ValueError("Hadis manbasidan ma'lumot olinmadi")

# 4. Hadis matnini ajratish
record = None

if isinstance(data, dict):
    if isinstance(data.get("hadith"), dict):
        record = data["hadith"]

    elif isinstance(data.get("hadiths"), list):
        record = next(
            (
                h for h in data["hadiths"]
                if str(h.get("hadithnumber")) == str(hadith_number)
            ),
            None
        )

    elif "text" in data:
        record = data

if not record or not record.get("text"):
    raise ValueError("Hadis matni topilmadi")

arabic = record["text"]

# 5. Groq orqali o'zbekchaga tarjima
translation_response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "qwen/qwen3.8-27b",
        "reasoning_effort": "none",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Сен араб тилидан ўзбек тилига таржима қилувчи "
                    "тажрибали исломий матнлар таржимонисан. "
                    "Матнни фақат ўзбек кириллида тўлиқ таржима қил. "
                    "Санад ва барча ровийларни ҳам таржима қил. "
                    "Ровийларнинг гапларини Расулуллоҳ "
                    "соллаллоҳу алайҳи васалламнинг сўзлари билан "
                    "аралаштирма. "
                    "Ҳадис атамаларини тўғри ишлат. "
                    "Ҳеч бир маънони туширма ва матнда йўқ "
                    "маълумотни қўшма. "
                    "Равон ва адабий ўзбек тилида ёз. "
                    "Фақат таржимани қайтар."
                )
            },
            {
                "role": "user",
                "content": "Қуйидаги ҳадисни таржима қил:\n\n" + arabic
            }
        ],
        "max_completion_tokens": 2048,
        "temperature": 0.1
    },
    timeout=90
)

if translation_response.status_code == 429:
    print("GROQ 429 XATOSI:", translation_response.text)
    raise ValueError("Groq limiti vaqtincha tugagan")

translation_response.raise_for_status()

translation_data = translation_response.json()

translation = (
    translation_data["choices"][0]["message"]["content"] or ""
).strip()

if not translation or len(translation) < 50:
    raise ValueError("Tarjima noto'g'ri yoki bo'sh qaytdi")

# 6. Telegramga yuborish
message = (
    f"📖 {book_name}\n"
    f"Ҳадис № {hadith_number}\n\n"
    f"{arabic}\n\n"
    f"🇺🇿 {translation}\n\n"
    f"Манба: {book_name}"
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

print("Hadis Telegramga yuborildi!")

# 7. Keyingi kun uchun navbatni yangilash
book_index += 1

if book_index >= len(books):
    book_index = 0
    hadith_number += 1

new_state = {
    "book_index": book_index,
    "hadith_number": hadith_number
}

with open(STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(new_state, f, ensure_ascii=False, indent=2)

# 8. Navbatni GitHubda saqlash
subprocess.run(
    ["git", "config", "user.name", "github-actions[bot]"],
    check=True
)

subprocess.run(
    ["git", "config", "user.email",
     "41898282+github-actions[bot]@users.noreply.github.com"],
    check=True
)

subprocess.run(["git", "add", STATE_FILE], check=True)

subprocess.run(
    ["git", "commit", "-m", "Update hadith sequence"],
    check=True
)

subprocess.run(["git", "push"], check=True)

print("Keyingi hadis navbati saqlandi!")

