import os
import requests
import json
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
URL = "https://www.apple.com/jp/shop/refurbished/iphone"
# Use a realistic User-Agent to avoid being blocked
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
CACHE_FILE = "cache.json"

# Update these targets for 128GB
TARGET_MODELS = ["iPhone 15 Pro", "1TB"]

def send_discord(message):
    try:
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": message}, timeout=30)
    except Exception as e:
        print(f"Failed to send Discord message: {e}")

def get_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}

try:
    response = requests.get(URL, headers=HEADERS, timeout=30)
    # Ensure the request was successful
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Apple's product titles are often in h3 tags within product cards
        product_elements = soup.find_all('h3') 
        
        found_items = []
        for item in product_elements:
            text = item.get_text().strip()
            # Verify both "iPhone 15 Pro" and "128GB" are present in the text
            if all(model.lower() in text.lower() for model in TARGET_MODELS):
                found_items.append(text)

        cache = get_cache()
        
        # Notify only if new items are found that weren't in the last check
        if found_items and cache.get("last_found") != found_items:
            message = "🚨 Apple Refurbished Japan Update!\nFound: " + ", ".join(found_items)
            send_discord(message)
            
            with open(CACHE_FILE, "w") as f:
                json.dump({"last_found": found_items}, f)
    else:
        print(f"Failed to retrieve page: {response.status_code}")

except Exception as e:
    send_discord(f"⚠️ Tracker Error: {e}")