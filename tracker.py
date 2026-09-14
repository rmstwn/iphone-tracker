import os
import requests
import re
import time
from bs4 import BeautifulSoup

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

# --- THE DIRECT LINK ATTACK ---
URLS = [
    "https://www.apple.com/jp/shop/refurbished/watch/apple-watch-series-11",
    "https://www.apple.com/jp/shop/refurbished/watch" 
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# --- EXACT TARGET CONFIGURATION ---
TARGET_MODELS = ["applewatchseries11"]
TARGET_VARIANTS = ["gps"] 

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
    
    # --- STRICT EXCLUSION: Block Cellular models instantly ---
    if "cellular" in spaceless:
        return False
        
    is_target_model = any(model in spaceless for model in TARGET_MODELS)
    is_target_variant = any(variant in spaceless for variant in TARGET_VARIANTS)
    
    return is_target_model and is_target_variant

# --- UPGRADED PRICE FINDER ---
def parse_html_products(soup):
    products = {}
    
    for tag in soup.find_all(['h2', 'h3', 'h4']):
        link = tag.find("a")
        
        if not link:
            continue
            
        text = link.get_text()
        display_text = re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()
        
        if not display_text or not matches_target(display_text):
            continue

        price = "Price not found"
        
        # Search the text elements that come AFTER this product's title
        for next_node in tag.find_all_next(string=True):
            
            # Skip the text that belongs to our current title
            if next_node.parent == tag or next_node.parent in tag.descendants:
                continue
                
            # THE BOUNDARY WALL: If we see the refurb tag again, we hit the next product! Stop!
            if "整備済製品" in next_node:
                break
                
            match = re.search(r"[\d,]+円", next_node)
            if match:
                price = match.group(0)
                break

        if price == "Price not found":
            print(f"DEBUG: Trashed ghost item with no price -> {display_text}")
            continue

        unique_key = generate_unique_key(display_text)
        products[unique_key] = {"key": unique_key, "name": display_text, "price": price}
        
    return products

try:
    master_found_products = {}

    for base_url in URLS:
        cache_buster_url = f"{base_url}?_={int(time.time())}"
        print(f"DEBUG: Fetching URL: {cache_buster_url}")
        
        response = requests.get(cache_buster_url, headers=HEADERS, timeout=30)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
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
            f"⌚ **{p['name']}**\n💰 **Price:** {p['price']}" for p in final_products
        ]
        
        main_url = "https://www.apple.com/jp/shop/refurbished/watch"
        message = (
            "🚨 **Apple Watch Refurbished Japan Update!**\n\n"
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