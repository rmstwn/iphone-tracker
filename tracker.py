import os
import json
import requests

URL = "https://www.apple.com/jp/shop/refurbished/iphone"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]

html = requests.get(URL, timeout=30).text

found = "iPhone 15 Pro" in html

try:
    with open("cache.json", "r") as f:
        cache = json.load(f)
except:
    cache = {"found": False}

if found and not cache["found"]:
    requests.post(
        WEBHOOK,
        json={
            "content":
            f"🚨 iPhone 15 Pro ditemukan!\n{URL}"
        }
    )

with open("cache.json", "w") as f:
    json.dump({"found": found}, f)