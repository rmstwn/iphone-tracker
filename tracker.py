import os
import requests
import json

WEBHOOK_URL = os.environ["DISCORD_WEBHOOK"]
URL = "https://www.apple.com/jp/shop/refurbished/iphone"
HEADERS = {"User-Agent": "Mozilla/5.0"}
KEYWORDS = ["iPhone 15 Pro 128GB"]
CACHE_FILE = "cache.json"

def send_discord(message):
    try:
        requests.post(WEBHOOK_URL, json={"content": message}, timeout=30)
    except Exception as e:
        print(f"Failed to send Discord message: {e}")

try:
    response = requests.get(URL, headers=HEADERS, timeout=30)
    html = response.text
    found = [k for k in KEYWORDS if k.lower() in html.lower()]

    # Robust cache loading
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                content = f.read().strip() # Read the content
                if content:                # Only try to parse if there is content
                    cache = json.loads(content)
        except json.JSONDecodeError:
            # If the file is corrupted, start fresh
            cache = {}

    # Notify only if there's a change
    if found and cache.get("last_found") != found:
        send_discord(f"🚨 Apple Refurbished Japan Update!\nFound: {', '.join(found)}\n{URL}")
        
        # Save to cache
        with open(CACHE_FILE, "w") as f:
            json.dump({"last_found": found}, f)

except Exception as e:
    send_discord(f"⚠️ Tracker Error: {e}")