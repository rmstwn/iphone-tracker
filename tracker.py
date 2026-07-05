import os
import requests
import json
import re
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
URL = "https://www.apple.com/jp/shop/refurbished/iphone"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
CACHE_FILE = "cache.json"

# --- EASY CONFIGURATION ZONE ---
TARGET_MODELS = ["iphone15pro", "iphone16pro"]
TARGET_STORAGES = ["128gb", "256gb", "512gb", "1tb"] # Added 1TB just in case!
# -------------------------------

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

def get_previously_seen_keys(cache, current_products):
    if "seen_keys" in cache:
        return set(cache["seen_keys"])
    return set()

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
        if not name:
            continue
            
        unique_key = generate_unique_key(name)
        products[unique_key] = {
            "key": unique_key,
            "name": re.sub(r"\s+", " ", name.replace("\xa0", " ")).strip(),
            "price": extract_price(data.get("offers", [])),
        }
    return products

def parse_h3_products(soup):
    products = {}
    
    for h3 in soup.find_all("h3"):
        link = h3.find("a")
        text = link.get_text() if link else h3.get_text()
        display_text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
        
        if not display_text:
            continue
            
        # 👁️ X-RAY VISION: This prints EVERYTHING the scraper sees!
        print(f"👁️ RAW SCRAPE: {display_text}")

        price = "Price not found"
        parent = h3.parent
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
    # Get everything from the page
    all_products = parse_json_ld_products(soup)
    for key, product in parse_h3_products(soup).items():
        all_products[key] = product
        
    # Filter only the targets
    filtered_products = []
    for product in all_products.values():
        if matches_target(product['name']):
            filtered_products.append(product)
            
    return filtered_products

try:
    print(f"DEBUG: Fetching URL: {URL}")
    response = requests.get(URL, headers=HEADERS, timeout=30)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        found_products = find_target_products(soup)
        print(f"DEBUG: Found {len(found_products)} matching target product(s).")

        cache = get_cache()
        previously_seen = get_previously_seen_keys(cache, found_products)
        current_keys = {product["key"] for product in found_products}
        new_products = [p for p in found_products if p["key"] not in previously_seen]

        if new_products:
            found_items = [
                f"📱 **{p['name']}**\n💰 **Price:** {p['price']}" for p in new_products
            ]
            message = (
                "🚨 **Apple Refurbished Japan Update!**\n\n"
                + "\n\n".join(found_items)
                + f"\n\n🔗 [Buy here]({URL})"
            )
            send_discord(message)

            with open(CACHE_FILE, "w") as f:
                json.dump({"seen_keys": sorted(list(current_keys))}, f)
                
        elif found_products:
            print("DEBUG: Items found, but all already in cache. No message sent.")
            if current_keys != previously_seen:
                with open(CACHE_FILE, "w") as f:
                    json.dump({"seen_keys": sorted(list(current_keys))}, f)
        else:
            print("DEBUG: No target items currently listed.")
            if previously_seen:
                with open(CACHE_FILE, "w") as f:
                    json.dump({"seen_keys": []}, f)

    else:
        print(f"DEBUG: Failed to retrieve page. Status code: {response.status_code}")

except Exception as e:
    print(f"⚠️ Tracker Error: {e} ")