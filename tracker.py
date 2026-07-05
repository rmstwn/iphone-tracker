import os
import requests
import json
import re
import time  # NEW: Required for the cache-buster
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
URL = "https://www.apple.com/jp/shop/refurbished/iphone"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- EASY CONFIGURATION ZONE ---
TARGET_MODELS = ["iphone15pro", "iphone16pro"]
TARGET_STORAGES = ["128gb", "256gb", "512gb", "1tb"]
# -------------------------------

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

def format_price(price):
    if isinstance(price, (int, float)):
        return f"{int(price):,}円"
    return str(price)

def extract_price(offers):
    if isinstance(offers, list) and offers:
        offers = offers[0]
    if isinstance(offers, dict) and offers.get("price") is not None:
        return format_price(offers["price"])
    return "Price not found"

def parse_json_ld_products(soup):
    products = {}
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
        if data.get("@type") != "Product":
            continue
            
        name = data.get("name", "")
        if not name or not matches_target(name):
            continue
            
        unique_key = generate_unique_key(name)
        products[unique_key] = {
            "key": unique_key,
            "name": re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip(),
            "price": extract_price(data.get("offers", [])),
        }
    return products

# --- UPGRADED: Now searches H2, H3, and H4 tags ---
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

def find_target_products(soup):
    products = parse_json_ld_products(soup)
    for key, product in parse_html_products(soup).items():
        products[key] = product
    return list(products.values())

try:
    # --- UPGRADED: Cache Buster appended to the URL ---
    cache_buster_url = f"{URL}?_={int(time.time())}"
    print(f"DEBUG: Fetching URL: {cache_buster_url}")
    
    response = requests.get(cache_buster_url, headers=HEADERS, timeout=30)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        found_products = find_target_products(soup)
        print(f"DEBUG: Found {len(found_products)} matching product(s).")

        if found_products:
            found_items = [
                f"📱 **{p['name']}**\n💰 **Price:** {p['price']}" for p in found_products
            ]
            
            message = (
                "🚨 **Apple Refurbished Japan Update!**\n\n"
                + "\n\n".join(found_items)
                + f"\n\n🔗 [Buy here]({URL})"
            )
            send_discord(message)
            
            for p in found_products:
                print(f"DEBUG: MATCH FOUND AND SENT -> {p['name']} | {p['price']}")
                
        else:
            print("DEBUG: No items matched the filtering criteria.")
            
    else:
        print(f"DEBUG: Failed to retrieve page. Status code: {response.status_code}")

except Exception as e:
    print(f"⚠️ Tracker Error: {e}")