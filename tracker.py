import os
import requests
import json
import re  # Required for finding the price pattern
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
URL = "https://www.apple.com/jp/shop/refurbished/iphone"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
CACHE_FILE = "cache.json"

# --- MODIFIED: Target conditions split into base model and storage options ---
BASE_MODEL = "iPhone 15 Pro"
TARGET_STORAGES = ["128GB", "256GB", "512GB"]  # Add more storage options if needed

def send_discord(message):
    try:
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": message}, timeout=30)
            print("DEBUG: Discord message sent successfully.")
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
        
        # Sticking exactly to the working method: raw <h3> tags
        product_elements = soup.find_all('h3') 
        print(f"DEBUG: Found {len(product_elements)} <h3> tags on the page.")
        
        found_items = []
        for item in product_elements:
            text = item.get_text().replace('\xa0', ' ').strip()
            
            # --- FIXED LOGIC: Must include "iPhone 15 Pro" but EXCLUDE "Max" ---
            is_correct_model = (BASE_MODEL.lower() in text.lower()) and ("max" not in text.lower())
            is_target_storage = any(storage.lower() in text.lower() for storage in TARGET_STORAGES)
            
            if is_correct_model and is_target_storage:
                
                # --- PRICE FINDER (No Classes Required) ---
                price = "Price not found"
                parent = item.parent
                
                # Climb up the HTML structure up to 5 levels to find the price block
                for _ in range(5):
                    if parent is None:
                        break
                    
                    for string in parent.stripped_strings:
                        match = re.search(r'[\d,]+円', string)
                        if match:
                            price = match.group(0)
                            break
                            
                    if price != "Price not found":
                        break
                        
                    parent = parent.parent
                # ----------------------------------------------

                # Format the text nicely for Discord
                final_item_text = f"📱 **{text}**\n💰 **Price:** {price}"
                found_items.append(final_item_text)
                print(f"DEBUG: MATCH FOUND -> {text} | {price}")
                
        cache = get_cache()
        
        if found_items:
            if cache.get("last_found") != found_items:
                message = "🚨 **Apple Refurbished Japan Update!**\n\n" + "\n\n".join(found_items) + f"\n\n🔗 [Buy here]({URL})"
                send_discord(message)
                
                with open(CACHE_FILE, "w") as f:
                    json.dump({"last_found": found_items}, f)
            else:
                print("DEBUG: Items found, but already in cache. No message sent.")
        else:
            print("DEBUG: No items matched the filtering criteria.")
            
    else:
        print(f"DEBUG: Failed to retrieve page. Status code: {response.status_code}")

except Exception as e:
    print(f"⚠️ Tracker Error: {e}")