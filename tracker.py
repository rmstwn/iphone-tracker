import os
import requests

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]

URL = "https://www.apple.com/jp/shop/refurbished/iphone"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

KEYWORDS = [
    "iPhone 15 Pro",
]

def send_discord(message):
    requests.post(
        WEBHOOK_URL,
        json={"content": message},
        timeout=30
    )

try:
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    html = response.text

    found = []

    for keyword in KEYWORDS:
        if keyword.lower() in html.lower():
            found.append(keyword)

    if found:
        send_discord(
            "🚨 Apple Refurbished Japan Update!\n\n"
            f"Found: {', '.join(found)}\n"
            f"{URL}"
        )

except Exception as e:
    send_discord(f"⚠️ Tracker Error: {e}")