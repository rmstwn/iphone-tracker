import os
import requests
import re
import time
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

# --- THE DIRECT LINK ATTACK ---
<<<<<<< HEAD
URLS = [
    "https://www.apple.com/jp/shop/refurbished/iphone/iphone-16-pro",
    "https://www.apple.com/jp/shop/refurbished/iphone/iphone-15-pro",
    "https://www.apple.com/jp/shop/refurbished/iphone" 
=======
# We visit the specific model pages to bypass Apple's lazy-loading on the main page
URLS = [
    "https://www.apple.com/jp/shop/refurbished/iphone/iphone-16-pro",
    "https://www.apple.com/jp/shop/refurbished/iphone/iphone-15-pro",
    "https://www.apple.com/jp/shop/refurbished/iphone" # Fallback main page
>>>>>>> 423310471fc128a0e1d74985d303067e03b9fc64
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

<<<<<<< HEAD
# --- ONLY VISIBLE HTML ALLOWED (No JSON Ghosts!) ---
=======
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

>>>>>>> 423310471fc128a0e1d74985d303067e03b9fc64
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
<<<<<<< HEAD
    # Dictionary to hold the real, verified phones
    master_found_products = {}

=======
    # We will store ALL found phones in this master dictionary to avoid duplicates
    master_found_products = {}

    # Loop through every URL in our list
>>>>>>> 423310471fc128a0e1d74985d303067e03b9fc64
    for base_url in URLS:
        cache_buster_url = f"{base_url}?_={int(time.time())}"
        print(f"DEBUG: Fetching URL: {cache_buster_url}")
        
        response = requests.get(cache_buster_url, headers=HEADERS, timeout=30)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
<<<<<<< HEAD
            # Extract ONLY from the visible HTML tags
=======
            # Extract from JSON-LD
            json_products = parse_json_ld_products(soup)
            for k, v in json_products.items():
                master_found_products[k] = v
                
            # Extract from HTML Tags
>>>>>>> 423310471fc128a0e1d74985d303067e03b9fc64
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
        
<<<<<<< HEAD
=======
        # Link back to the main refurb page in the Discord message
>>>>>>> 423310471fc128a0e1d74985d303067e03b9fc64
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