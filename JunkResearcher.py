import os
import sqlite3
import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor
from googlesearch import search
from openai import OpenAI, OpenAIError
from urllib.parse import urlparse

DB_NAME = "auction_items.db"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
BASE_URL = "https://www.peterfrancis.co.uk"

exclude_patterns = [
    r"easy.?live.?auction"
]

art_sites = ["invaluable.com", "artprice.com", "artnet.com", "mutualart.com", "christies.com", "sothebys.com"]

def is_excluded(url):
    return any(re.search(pattern, url, re.IGNORECASE) for pattern in exclude_patterns)

def is_valid_url(url):
    try:
        parsed = urlparse(url)
        return all([parsed.scheme, parsed.netloc])
    except:
        return False

def is_art_item(name, description):
    return bool(re.search(r"\b(artist|painting|oil|canvas|watercolour|print|drawing|lithograph|signed)\b", f"{name} {description}", re.IGNORECASE))

def generate_search_query(item, is_art=False):
    prompt = (
        "Given these item details, generate a broad Google search query to find comparable market values. "
        "For artwork, include artist, medium, and subject.\n\n"
        f"Title: {item['name']}\nDescription: {item['description']}\n\nReturn only the search query."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        query = response.choices[0].message.content.strip()
        print(f"[OpenAI] Generated Query: {query}")
        return query
    except OpenAIError as e:
        print(f"[OpenAI Error] {e}")
        return None

def extract_price_from_page(content):
    pattern = re.compile(r'(?:€|EUR|\$|£)\s?\d{1,3}(?:[,.]\d{3})*(?:[.,]\d{2})?')
    match = pattern.search(content)
    if match:
        return match.group().replace('EUR', '€').replace(',', '').strip()
    return None

def analyze_market_value(scraped_text):
    prompt = (
        "Based on the following listings, estimate the item's market value in Euros and briefly explain why. "
        "If uncertain, reply 'None' and briefly explain why.\n\n"
        f"{scraped_text[:3000]}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        reasoning = response.choices[0].message.content.strip()
        print(f"[OpenAI Reasoning] {reasoning}")
        match = re.search(r"(\d+[.,]?\d*)", reasoning.replace(',', ''))
        value = float(match.group(1)) if match else None
        return value, reasoning
    except OpenAIError as e:
        print(f"[OpenAI Error] {e}")
        return None, "OpenAI analysis error."

def get_comparable_price_and_urls(query, is_art=False):
    combined_text = ""
    urls_collected = []

    try:
        results = list(search(query, num_results=10))
        for url in results:
            if len(urls_collected) >= 3:
                break
            if not url or not is_valid_url(url) or is_excluded(url):
                continue
            if is_art and not any(site in url for site in art_sites):
                continue
            print(f"[Google] Checking URL: {url}")
            response = requests.get(url, timeout=10)
            if response.ok:
                price = extract_price_from_page(response.text)
                if price:
                    urls_collected.append((url, price))
                combined_text += response.text[:2000]
    except Exception as e:
        print(f"[Google Search Error] {e}")
        time.sleep(10)

    estimated_price, reasoning = analyze_market_value(combined_text)
    return estimated_price, urls_collected, reasoning

def domain_from_url(url):
    return urlparse(url).netloc.replace("www.", "")

def format_analysis(price, urls, reasoning):
    if price:
        analysis = f"<b>Estimated Value:</b> €{price}<br><b>Reasoning:</b> {reasoning}<br><b>Sources:</b> "
        analysis += " | ".join(
            [f'<a href="{url}" target="_blank">{domain_from_url(url)}</a> ({price})' for url, price in urls]
        )
        return analysis
    return f"No comparable price found. Reasoning: {reasoning}"

def analyze_single_item(item):
    item_id, name, description, current_bid = item
    print(f"\n[Analysis] Item {item_id}: {name}")

    if re.search(r'\bafter\b', name, re.IGNORECASE):
        analysis = "Dropped: Reproduction"
        print("[Analysis Skipped] Dropped as reproduction.")
    else:
        is_art = is_art_item(name, description)
        query = generate_search_query({'name': name, 'description': description}, is_art)
        if not query:
            analysis = "Failed to generate search query."
        else:
            comp_price, urls, reasoning = get_comparable_price_and_urls(query, is_art)
            bid_value = float(re.sub(r"[^\d.]", "", current_bid or "0"))
            premium_bid = bid_value * 1.30

            if comp_price and premium_bid < (0.3 * comp_price):
                analysis = format_analysis(comp_price, urls, reasoning)
            else:
                analysis = "Dropped: Not a significant bargain."
                print("[Dropped] Not a significant bargain.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE lot_items SET analysis = ? WHERE id = ?", (analysis, item_id))
    conn.commit()
    conn.close()
    print(f"[Analysis Completed] Item {item_id}: {analysis}")

def analyze_items():
    while True:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, description, current_bid FROM lot_items WHERE analysis IS NULL OR analysis = '' LIMIT 5")
        items = cursor.fetchall()
        conn.close()

        if not items:
            print("Waiting for new items...")
            time.sleep(10)
            continue

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(analyze_single_item, items)

if __name__ == '__main__':
    analyze_items()
