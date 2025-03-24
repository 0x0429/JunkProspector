import os
import re
import sqlite3
import time
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

import requests
from googlesearch import search
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "BASE AUCTION URL HERE"
START_URL = "URL FOR LOT1"
DB_NAME = "auction_items.db"
MAX_ITEMS = 10

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS lot_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            current_bid TEXT,
            description TEXT,
            url TEXT,
            analysis TEXT
        )
    ''')
    conn.commit()
    return conn


def alter_table(conn):
    c = conn.cursor()
    c.execute("PRAGMA table_info(lot_items)")
    columns = [info[1] for info in c.fetchall()]
    if "current_bid" not in columns:
        c.execute("ALTER TABLE lot_items ADD COLUMN current_bid TEXT")
    if "description" not in columns:
        c.execute("ALTER TABLE lot_items ADD COLUMN description TEXT")
    if "analysis" not in columns:
        c.execute("ALTER TABLE lot_items ADD COLUMN analysis TEXT")
    conn.commit()


def save_item(conn, name, current_bid, description, url, analysis=""):
    c = conn.cursor()
    c.execute('''
        INSERT INTO lot_items (name, current_bid, description, url, analysis)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, current_bid, description, url, analysis))
    conn.commit()


def setup_driver():
    from selenium.webdriver.chrome.service import Service
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(service=Service(), options=options)


def parse_lot_details(driver):
    try:
        name_element = driver.find_element(By.CSS_SELECTOR, "h1.lot-desc-h1")
        lot_name = name_element.text.strip()
    except Exception:
        lot_name = driver.title.strip() or "Unnamed Lot"

    try:
        bid_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "timedBid"))
        )
        current_bid = bid_element.text.strip()
    except Exception:
        current_bid = "N/A"

    desc_elements = driver.find_elements(By.CSS_SELECTOR, "p.translate")
    description = " ".join(elem.text.strip() for elem in desc_elements)
    return lot_name, current_bid, description


def find_next_lot_url(driver):
    try:
        next_link = driver.find_element(By.XPATH, "//a[@rel='next']")
        href = next_link.get_attribute("href")
        return urljoin(BASE_URL, href) if href else None
    except Exception:
        return None


def qualifies_for_analysis(item):
    name = item['name'].lower()
    generic_keywords = ['pendant', 'brooch', 'jewellery', 'costume', 'accessory']
    special_keywords = ['antique', 'artist', 'signed', 'vintage', 'handcrafted']
    return not any(g in name for g in generic_keywords) or any(s in name for s in special_keywords)


def generate_search_query(item):
    prompt = (
        "Rewrite the following item details as an optimized Google search query "
        "to find online listings or auctions for comparable items. "
        "Include brand, descriptors, materials, but avoid exact phrase matches.\n\n"
        f"Item Title: {item['name']}\n"
        f"Description: {item['description']}\n\n"
        "Return only the search query."
    )
    payload = {
        "model": "gpt-4o",
        "input": prompt,
        "temperature": 0.3,
        "store": False
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    api_url = "https://api.openai.com/v1/responses"
    try:
        r = requests.post(api_url, headers=headers, json=payload, timeout=20)
        data = r.json()
        for out in data.get("output", []):
            if out.get("role") == "assistant":
                return "\n".join([c.get("text", "") for c in out.get("content", [])])
        return "No query generated."
    except Exception as e:
        return f"Error generating search query: {e}"


def get_comparable_url(query, max_results=5, retries=3, delay=60):
    for attempt in range(1, retries + 1):
        try:
            print(f"[Attempt {attempt}] Google search query: {query}")
            results = list(search(query, num_results=max_results))
            for url in results:
                if any(x in url.lower() for x in ["EXCLUSION1", "EXCLUSION2", "EXCLUSION3"]):
                    continue
                page = requests.get(url, timeout=10)
                if not page.ok:
                    continue
                price = extract_price_from_page(page.text)
                if price:
                    print(f"[Attempt {attempt}] Found URL with price: {url}")
                    return url
            return "No comparable URL found."
        except Exception as e:
            print(f"[Attempt {attempt}] Google search error: {e}")
            if "429" in str(e) or "rate limit" in str(e).lower():
                time.sleep(delay)
            else:
                return f"Search error: {e}"
    return "Search error: Rate limit exceeded"


def extract_price_from_page(content):
    pattern = re.compile(r'(\$|€|(?:\\s?EUR\\s?))\\s?(\d{1,3}(?:[,.]\d{3})*(?:[.,]\d+)?)')
    match = pattern.search(content)
    if match:
        symbol = match.group(1).strip()
        value = match.group(2).replace(',', '.').replace('..', '.')
        return f"{symbol}{value}"
    return None


def get_comparable_price(url):
    try:
        r = requests.get(url, timeout=10)
        if r.ok:
            return extract_price_from_page(r.text) or "Price not found on page."
        return f"Error fetching page: {r.status_code}"
    except Exception as e:
        return f"Error fetching page: {e}"


def parse_price_to_float(price_str):
    if not price_str or price_str in ["N/A", "Price not found on page."]:
        return None
    value = re.sub(r'[^0-9.]', '', price_str)
    try:
        return float(value)
    except ValueError:
        return None


def analyze_item(item):
    if not qualifies_for_analysis(item):
        return "Skipped generic item."

    query = generate_search_query(item)
    if "error" in query.lower():
        return query

    comp_url = get_comparable_url(query)
    if not comp_url.startswith("http"):
        return "No valid comparable URL identified."

    comp_price_raw = get_comparable_price(comp_url)
    auction_price = parse_price_to_float(item['current_bid'])
    comp_price = parse_price_to_float(comp_price_raw)

    if auction_price is None or comp_price is None:
        return "Comparable price or auction price not extracted."

    auction_price_with_premium = auction_price * 1.30

    if auction_price_with_premium < comp_price * 0.30:
        return (
            f"Bargain detected. Auction price (incl. 30% premium): €{auction_price_with_premium:.2f}, "
            f"Comparable price: €{comp_price:.2f}. URL: {comp_url}"
        )

    return "No significant bargain detected."


def main():
    conn = init_db()
    alter_table(conn)
    driver = setup_driver()
    current_url = START_URL
    lot_count = 0

    while current_url and lot_count < MAX_ITEMS:
        print(f"\nLoading: {current_url}")
        driver.get(current_url)
        time.sleep(3)
        name, bid, desc = parse_lot_details(driver)
        print(f"Found lot: {name} - Current Bid: {bid}")

        item = {"name": name, "current_bid": bid, "description": desc, "url": current_url}
        analysis = analyze_item(item)
        save_item(conn, name, bid, desc, current_url, analysis)

        print(f"Analysis updated for {current_url}:\n{analysis}\n")

        lot_count += 1
        current_url = find_next_lot_url(driver)

    driver.quit()
    conn.close()
    print("✅ Done.")


if __name__ == "__main__":
    main()
