import sqlite3
import time
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DB_NAME = "auction_items.db"
BASE_URL = "https://www.peterfrancis.co.uk"

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

def save_item(conn, name, current_bid, description, url):
    c = conn.cursor()
    c.execute('''
        INSERT INTO lot_items (name, current_bid, description, url)
        VALUES (?, ?, ?, ?)
    ''', (name, current_bid, description, url))
    conn.commit()

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)

def parse_lot_details(driver):
    try:
        lot_name = driver.find_element(By.CSS_SELECTOR, "h1.lot-desc-h1").text.strip()
    except:
        lot_name = driver.title.strip() or "Unnamed Lot"

    try:
        current_bid = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "timedBid"))
        ).text.strip()
    except:
        current_bid = "N/A"

    description = " ".join([elem.text.strip() for elem in driver.find_elements(By.CSS_SELECTOR, "p.translate")])
    return lot_name, current_bid, description

def find_next_lot_url(driver):
    try:
        next_link = driver.find_element(By.XPATH, "//a[@rel='next']").get_attribute("href")
        return urljoin(BASE_URL, next_link) if next_link else None
    except:
        return None

def scrape_auction_items(start_url, max_items=1000):
    conn = init_db()
    driver = setup_driver()
    current_url = start_url
    lot_count = 0

    while current_url and lot_count < max_items:
        print(f"\nLoading: {current_url}")
        driver.get(current_url)
        time.sleep(3)

        name, bid, desc = parse_lot_details(driver)
        print(f"Found lot: {name} - Current Bid: {bid}")

        save_item(conn, name, bid, desc, current_url)

        lot_count += 1
        current_url = find_next_lot_url(driver)

    driver.quit()
    conn.close()
    print("✅ Scraping completed.")
