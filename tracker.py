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

TARGET_STORAGES = ["128gb", "256gb", "512gb"]

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

# --- THE BULLETPROOF MATCHER ---
def matches_target(name):
    # 1. Lowercase everything
    lower_name = name.lower()
    
    # 2. Remove ALL standard spaces, non-breaking spaces, and Japanese wide-spaces
    # This prevents Apple's weird formatting from breaking the script.
    spaceless = lower_name.replace(" ", "").replace("\xa0", "").replace(" ", "")
    
    # 3. Exclude Max and Plus
    if "max" in spaceless or "plus" in spaceless:
        return False
        
    # 4. Must be either 15 Pro or 16 Pro
    if "iphone15pro" not in spaceless and "iphone16pro" not in spaceless:
        return False
        
    # 5. Must match your target storage sizes
    return any(storage in spaceless for storage in TARGET_STORAGES)
# -------------------------------

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
            
        offers = data.get("offers", [])
        
        # Use the name as the key to prevent duplicate Discord messages
        key = name 
        
        products[key] = {
            "key": key,
            "name": name,
            "price": extract_price(offers),
        }
    return products

def parse_h3_products(soup):
    products = {}
    
    for h3 in soup.find_all("h3"):
        link = h3.find("a")
        text = link.get_text() if link else h3.get_text()
        
        # Clean up the text visually for your Discord alert
        display_text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
        
        if not display_text or not matches_target(display_text):
            continue

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

        products[display_text] = {"key": display_text, "name": display_text, "price": price}
    return products

def find_target_products(soup):
    products = parse_json_ld_products(soup)
    for key, product in parse_h3_products(soup).items():
        products.setdefault(key, product)
    return list(products.values())

try:
    print(f"DEBUG: Fetching URL: {URL}")
    response = requests.get(URL, headers=HEADERS, timeout=30)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        found_products = find_target_products(soup)
        print(f"DEBUG: Found {len(found_products)} matching product(s).")

        for product in found_products:
            print(f"DEBUG: MATCH FOUND -> {product['name']} | {product['price']}")

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
                json.dump({"seen_keys": sorted(current_keys)}, f)
        elif found_products:
            print("DEBUG: Items found, but all already in cache. No message sent.")
            if current_keys != previously_seen:
                with open(CACHE_FILE, "w") as f:
                    json.dump({"seen_keys": sorted(current_keys)}, f)
        else:
            print("DEBUG: No items matched the filtering criteria.")
            if previously_seen:
                with open(CACHE_FILE, "w") as f:
                    json.dump({"seen_keys": []}, f)

    else:
        print(f"DEBUG: Failed to retrieve page. Status code: {response.status_code}")

except Exception as e:
    print(f"⚠️ Tracker Error: {e}")