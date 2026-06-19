import os
import requests
import json
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
URL = "https://www.apple.com/jp/shop/refurbished/iphone"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
CACHE_FILE = "cache.json"

# Target specific models
TARGET_MODELS = ["iPhone 15 Pro", "128GB"]

def send_discord(message):
    try:
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": message}, timeout=30)
            print("DEBUG: Discord message sent successfully.")
        else:
            print("DEBUG: WEBHOOK_URL is not set!")
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
    print(f"DEBUG: Fetching URL: {URL}")
    response = requests.get(URL, headers=HEADERS, timeout=30)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for h3 tags (common for product titles)
        product_elements = soup.find_all('h3') 
        print(f"DEBUG: Found {len(product_elements)} <h3> tags on the page.")
        
        found_items = []
        for item in product_elements:
            text = item.get_text().strip()
            # If you want to see EVERY item it finds, uncomment the line below:
            # print(f"DEBUG: Checking item: {text}") 
            
            if all(model.lower() in text.lower() for model in TARGET_MODELS):
                found_items.append(text)
                print(f"DEBUG: MATCH FOUND -> {text}")

        cache = get_cache()
        
        if found_items:
            if cache.get("last_found") != found_items:
                message = "🚨 Apple Refurbished Japan Update!\nFound: " + ", ".join(found_items)
                send_discord(message)
                
                with open(CACHE_FILE, "w") as f:
                    json.dump({"last_found": found_items}, f)
            else:
                print("DEBUG: Items found, but they are already in the cache. No message sent.")
        else:
            print("DEBUG: No items matched the TARGET_MODELS criteria.")
            
    else:
        print(f"DEBUG: Failed to retrieve page. Status code: {response.status_code}")

except Exception as e:
    error_msg = f"⚠️ Tracker Error: {e}"
    print(error_msg)
    send_discord(error_msg)