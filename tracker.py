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

TARGET_STORAGES = ["128GB", "256GB", "512GB"]

# Match iPhone 15/16 Pro but not Pro Max or Plus (handles Apple's non-breaking spaces)
MODEL_PATTERN = re.compile(r"iphone\s+(?:15|16)\s+pro(?:\s|$|-|\d)", re.IGNORECASE)
PRO_MAX_OR_PLUS = re.compile(r"pro\s*max|\bplus\b", re.IGNORECASE)


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

    # Migrate old list-based cache
    seen_names = set()
    for item in cache.get("last_found", []):
        match = re.search(r"\*\*(.+?)\*\*", item)
        if match:
            seen_names.add(normalize_text(match.group(1)))

    if not seen_names:
        return set()

    return {
        product["key"]
        for product in current_products
        if product["name"] in seen_names
    }


def normalize_text(text):
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def matches_target(name):
    normalized = normalize_text(name)
    lower = normalized.lower()
    if PRO_MAX_OR_PLUS.search(lower):
        return False
    if not MODEL_PATTERN.search(lower):
        return False
    return any(storage.lower() in lower for storage in TARGET_STORAGES)


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
            
        name = normalize_text(data.get("name", ""))
        if not name or not matches_target(name):
            continue
            
        offers = data.get("offers", [])
        
        # FIX 2: Use the product name as the key to prevent duplicates
        key = name 
        
        products[key] = {
            "key": key,
            "name": name,
            "price": extract_price(offers),
        }
    return products


def parse_h3_products(soup):
    products = {}
    
    # FIX 1: Search all h3 tags on the entire page, bypassing the single-grid limitation
    for h3 in soup.find_all("h3"):
        link = h3.find("a")
        text = normalize_text(link.get_text() if link else h3.get_text())
        if not text or not matches_target(text):
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

        products[text] = {"key": text, "name": text, "price": price}
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