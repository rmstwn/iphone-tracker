import os
import requests
import re
import time
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

# --- THE DIRECT LINK ATTACK ---
URLS = [
    "https://www.apple.com/jp/shop/refurbished/iphone/iphone-16-pro",
    "https://www.apple.com/jp/shop/refurbished/iphone/iphone-15-pro",
    "https://www.apple.com/jp/shop/refurbished/iphone" 
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

TARGET_MODELS = ["iphone15pro", "iphone16pro"]
TARGET_STORAGES = ["128gb", "256gb", "512gb", "1tb"]

def send_discord(message):
    try:
        if WEBHOOK_URL:
            requests.post(WEBHOOK_URL, json={"content": message}, timeout=30)
            print("DEBUG: Discord message sent successfully.")
    except Exception as e:
        print(f"Failed to send Discord message: {e}")

def generate_unique_key(name):
    return name.lower().replace(" ", "").replace("\xa0", "").replace(" ", "")

def matches_target(name):
    spaceless = generate_unique_key(name)
    if "max" in spaceless or "plus" in spaceless:
        return False
    is_target_model = any(model in spaceless for model in TARGET_MODELS)
    is_target_storage = any(storage in spaceless for storage in TARGET_STORAGES)
    return is_target_model and is_target_storage

# --- ONLY VISIBLE HTML ALLOWED (No JSON Ghosts!) ---
def parse_html_products(soup):
    products = {}
    for tag in soup.find_all(['h2', 'h3', 'h4']):
        link = tag.find("a")
        text = link.get_text() if link else tag.get_text()
        display_text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
        
        if not display_text or not matches_target(display_text):
            continue

        price = "Price not found"
        parent = tag.parent
        for _ in range(5):
            if parent is None:
                break
            for string in parent.stripped_strings:
                match = re.search(r"[\d,]+円", string)
                if match:
                    price = match.group(0)
                    break
            if price != "Price not found":
                break
            parent = parent.parent

        unique_key = generate_unique_key(display_text)
        products[unique_key] = {"key": unique_key, "name": display_text, "price": price}
    return products

try:
    # Dictionary to hold the real, verified phones
    master_found_products = {}

    for base_url in URLS:
        cache_buster_url = f"{base_url}?_={int(time.time())}"
        print(f"DEBUG: Fetching URL: {cache_buster_url}")
        
        response = requests.get(cache_buster_url, headers=HEADERS, timeout=30)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract ONLY from the visible HTML tags
            html_products = parse_html_products(soup)
            for k, v in html_products.items():
                master_found_products[k] = v
        else:
            print(f"DEBUG: Failed to retrieve {base_url}. Status: {response.status_code}")
            
    # --- SEND THE DISCORD ALERT ---
    final_products = list(master_found_products.values())
    print(f"DEBUG: Grand Total Found: {len(final_products)} target product(s).")

    if final_products:
        found_items = [
            f"📱 **{p['name']}**\n💰 **Price:** {p['price']}" for p in final_products
        ]
        
        main_url = "https://www.apple.com/jp/shop/refurbished/iphone"
        message = (
            "🚨 **Apple Refurbished Japan Update!**\n\n"
            + "\n\n".join(found_items)
            + f"\n\n🔗 [Buy here]({main_url})"
        )
        send_discord(message)
        
        for p in final_products:
            print(f"DEBUG: MATCH FOUND AND SENT -> {p['name']} | {p['price']}")
            
    else:
        print("DEBUG: No items matched the filtering criteria across any URLs.")

except Exception as e:
    print(f"⚠️ Tracker Error: {e}")