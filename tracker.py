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

TARGET_MODELS = ["iPhone 15 Pro", "1TB"]

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
        
        # We start by finding the <h3> titles
        product_elements = soup.find_all('h3', class_='rf-refurb-producttile-title') 
        print(f"DEBUG: Found {len(product_elements)} <h3> tags on the page.")
        
        found_items = []
        for item in product_elements:
            # Clean the text to handle the hidden &nbsp;
            text = item.get_text().replace('\xa0', ' ').strip()
            
            if all(model.lower() in text.lower() for model in TARGET_MODELS):
                
                # --- NEW PRICE EXTRACTION USING HTML CLASSES ---
                price = "Price not found"
                
                # Step 1: Find the parent <li> container that holds the whole product card
                product_card = item.find_parent('li', class_='rf-refurb-producttile')
                
                if product_card:
                    # Step 2: Find the specific span inside this card that holds the price
                    price_span = product_card.find('span', class_='rf-refurb-producttile-currentprice')
                    if price_span:
                        price = price_span.get_text().strip()
                # -----------------------------------------------
                
                # Format the text for Discord
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
            print("DEBUG: No items matched the TARGET_MODELS criteria.")
            
    else:
        print(f"DEBUG: Failed to retrieve page. Status code: {response.status_code}")

except Exception as e:
    print(f"⚠️ Tracker Error: {e}")