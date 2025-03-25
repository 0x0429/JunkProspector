import sys
from concurrent.futures import ThreadPoolExecutor
from JunkReader import scrape_auction_items
from JunkResearcher import analyze_items

def main(start_url):
    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(scrape_auction_items, start_url)
        executor.submit(analyze_items)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python JunkProspector.py [START_URL]")
    else:
        main(sys.argv[1])
