# JunkCompare.py
import sqlite3

DB_NAME = "auction_items.db"
BARGAIN_THRESHOLD = 0.3  # 70% cheaper than market price after adding premium
BUYER_PREMIUM = 0.30

def parse_price(analysis):
    try:
        price_str = analysis.split('€')[1].split()[0]
        return float(price_str)
    except (IndexError, ValueError):
        return None

def compare_prices():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT name, current_bid, analysis, url FROM lot_items")
    items = cursor.fetchall()

    for name, current_bid, analysis, url in items:
        market_price = parse_price(analysis)
        try:
            auction_price = float(current_bid.replace('€', '').replace(',', '').strip())
        except ValueError:
            auction_price = None

        if market_price and auction_price:
            total_auction_price = auction_price * (1 + BUYER_PREMIUM)
            if total_auction_price < market_price * BARGAIN_THRESHOLD:
                print(f"Bargain Found: {name}")
                print(f"Auction Price (with premium): €{total_auction_price:.2f}")
                print(f"Estimated Market Price: €{market_price:.2f}")
                print(f"Link: {url}\n")

    conn.close()

if __name__ == '__main__':
    compare_prices()
