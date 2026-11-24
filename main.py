
import os
import json
import requests
import subprocess

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
QURAN_CHAT_ID = os.getenv("QURAN_CHAT_ID")
GROQ_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN or not CHAT_ID or not GROQ_KEY or not QURAN_CHAT_ID:
    raise ValueError("Telegram, Quran yoki Groq sozlamalari topilmadi")


# ==================================================
# UMUMIY FUNKSIYALAR
# ==================================================

def send_telegram(chat_id, message):
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message
        },
        timeout=40
    )
    response.raise_for_status()

    result = response.json()

    if not result.get("ok"):
        raise ValueError(f"Telegram xatosi: {result}")


def save_to_github(files, commit_message):
    subprocess.run(
        ["git", "config", "user.name", "github-actions[bot]"],
        check=True
    )

    subprocess.run(
        [
            "git", "config", "user.email",
            "41898282+github-actions[bot]@users.noreply.github.com"
        ],
        check=True
    )

    subprocess.run(["git", "add"] + files, check=True)

    check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"]
    )

    if check.returncode == 1:
        subprocess.run(
            ["git", "commit", "-m", commit_message],
            check=True
        )
        subprocess.run(["git", "push"], check=True)

    elif check.returncode != 0:
        raise ValueError("Git tekshirishda xato")





# ==================================================
# 2. QUR'ON - HAR KUNI 5 TA OYAT
# ==================================================

QURAN_STATE_FILE = "quran_state.json"
TRANSLATION_KEY = "uzbek_mansour"
QURAN_DAILY_COUNT = 5

# Birinchi kun Fotiha 1:1 dan boshlanadi
if os.path.exists(QURAN_STATE_FILE):
    with open(QURAN_STATE_FILE, "r", encoding="utf-8") as f:
        quran_state = json.load(f)
else:
    quran_state = {
        "sura_number": 1,
        "aya_number": 1
    }

sura_number = int(quran_state["sura_number"])
aya_number = int(quran_state["aya_number"])

if not (1 <= sura_number <= 114) or aya_number < 1:
    raise ValueError("Qur'on navbati noto'g'ri")

print(
    f"Qur'on boshlanishi: "
    f"{sura_number}:{aya_number}"
)

# QuranEnc tarjimalari ro'yxatini olish
list_response = requests.get(
    "https://quranenc.com/api/v1/translations/list/uz?localization=uz",
    timeout=30
)

list_response.raise_for_status()

list_data = list_response.json()

if isinstance(list_data, dict):
    translations = list_data.get("translations", [])
elif isinstance(list_data, list):
    translations = list_data
else:
    translations = []

translator_info = next(
    (
        item for item in translations
        if item.get("key") == TRANSLATION_KEY
    ),
    None
)

if not translator_info:
    available_keys = [
        item.get("key")
        for item in translations
    ]

    raise ValueError(
        "Alauddin Mansour tarjimasi topilmadi. "
        f"Mavjud kalitlar: {available_keys}"
    )

version = translator_info.get("version")

if not version:
    raise ValueError("Tarjima versiyasi aniqlanmadi")

# Suralar ma'lumotini olish uchun funksiya
sura_cache = {}


def get_sura(number):
    if number not in sura_cache:
        url = (
            "https://quranenc.com/api/v1/translation/sura/"
            f"{TRANSLATION_KEY}/{number}"
        )

        response = requests.get(url, timeout=40)
        response.raise_for_status()

        data = response.json()

        if isinstance(data, dict):
            result = data.get("result", [])
        else:
            result = data

        if not isinstance(result, list) or not result:
            raise ValueError(
                f"{number}-sura ma'lumotlari olinmadi"
            )

        sura_cache[number] = result

    return sura_cache[number]


# Ketma-ket 5 ta oyatni yig'ish
selected_ayat = []

current_sura = sura_number
current_aya = aya_number

for i in range(QURAN_DAILY_COUNT):

    if current_sura > 114:
        current_sura = 1
        current_aya = 1

    sura_data = get_sura(current_sura)

    aya_data = next(
        (
            item for item in sura_data
            if int(item.get("aya", 0)) == current_aya
        ),
        None
    )

    if not aya_data:
        raise ValueError(
            f"Oyat topilmadi: {current_sura}:{current_aya}"
        )

    arabic_text = aya_data.get("arabic_text", "").strip()
    uzbek_text = aya_data.get("translation", "").strip()

    if not arabic_text or not uzbek_text:
        raise ValueError(
            f"Oyat matni bo'sh: {current_sura}:{current_aya}"
        )

    selected_ayat.append({
        "sura": current_sura,
        "aya": current_aya,
        "arabic": arabic_text,
        "translation": uzbek_text
    })

    # Keyingi oyatga o'tish
    last_aya = max(
        int(item["aya"]) for item in sura_data
    )

    if current_aya < last_aya:
        current_aya += 1
    else:
        current_sura += 1
        current_aya = 1

# Qur'on xabarlarini tayyorlash
message_parts = []

for item in selected_ayat:
    part = (
        f"📖 {item['sura']}-сура, "
        f"{item['aya']}-оят\n\n"
        f"{item['arabic']}\n\n"
        f"🇺🇿 {item['translation']}"
    )

    message_parts.append(part)

# Telegram 4096 belgilik cheklovini hisobga olib,
# oyatlarni kerak bo'lsa bir nechta xabarga ajratish
header = "📖 ҚУРЪОНИ КАРИМ\n\n"
footer = (
    f"\n\nТаржимон: Алоуддин Мансур"
    f"\nМанба: QuranEnc.com"
    f"\nТаржима версияси: {version}"
)

messages = []
current_message = header

for part in message_parts:
    addition = part + "\n\n"

    if len(current_message) + len(addition) + len(footer) > 3900:
        if current_message.strip() != header.strip():
            messages.append(current_message.rstrip())
            current_message = header

    if len(current_message) + len(addition) + len(footer) > 3900:
        raise ValueError(
            "Bitta oyat Telegram xabar chegarasidan oshdi"
        )

    current_message += addition

current_message += footer
messages.append(current_message)

# Barcha xabarlarni Qur'on kanaliga yuborish
for message in messages:
    send_telegram(QURAN_CHAT_ID, message)

print("Qur'on kanaliga 5 ta oyat yuborildi!")

# Keyingi kun uchun navbatni saqlash
new_quran_state = {
    "sura_number": current_sura,
    "aya_number": current_aya
}

with open(QURAN_STATE_FILE, "w", encoding="utf-8") as f:
    json.dump(
        new_quran_state,
        f,
        ensure_ascii=False,
        indent=2
    )

save_to_github(
    [QURAN_STATE_FILE],
    "Update Quran sequence"
)

print("Qur'on navbati GitHubda saqlandi!")
print("Ikkala kanalga yuborish yakunlandi!")


