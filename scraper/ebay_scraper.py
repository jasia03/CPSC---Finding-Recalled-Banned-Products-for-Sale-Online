import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import time

print("Starting eBay scraper...")

# Step 1 — load our recall database so we know what to search for
conn = sqlite3.connect('data/cpsc_recalls.db')
recalls = pd.read_sql("SELECT * FROM recalls", conn)
conn.close()

print(f"Loaded {len(recalls)} recalled products to search for")
print(f"Sample products we will search:")
print(recalls['Name of product'].head(5).tolist())

# Step 2 — function that searches eBay for one product
def search_ebay(product_name, recall_number):
    
    # clean up the product name for use in a URL
    # eBay search URL uses + between words
    search_query = product_name.replace(' ', '+')
    url = f"https://www.ebay.com/sch/i.html?_nkw={search_query}&LH_ItemCondition=3000"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"  Failed to get results for {product_name} - status {response.status_code}")
            return []
        
        # parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # find all listing items on the page
        listings = soup.find_all('li', class_='s-item')
        
        results = []
        for listing in listings:
            
            # extract title
            title_tag = listing.find('div', class_='s-item__title')
            title = title_tag.text.strip() if title_tag else ''
            
            # skip the first ghost listing ebay always adds
            if title == 'Shop on eBay' or title == '':
                continue
            
            # extract price
            price_tag = listing.find('span', class_='s-item__price')
            price = price_tag.text.strip() if price_tag else ''
            
            # extract link
            link_tag = listing.find('a', class_='s-item__link')
            link = link_tag['href'] if link_tag else ''
            
            # extract condition
            condition_tag = listing.find('span', class_='SECONDARY_INFO')
            condition = condition_tag.text.strip() if condition_tag else ''
            
            results.append({
                'recall_number': recall_number,
                'searched_product': product_name,
                'listing_title': title,
                'price': price,
                'condition': condition,
                'url': link,
                'platform': 'eBay'
            })
        
        return results
    
    except Exception as e:
        print(f"  Error searching for {product_name}: {e}")
        return []

        # Step 3 — test on first 5 products only
print("\nTesting eBay search on 5 products...")

test_recalls = recalls.head(5)
all_listings = []

for index, row in test_recalls.iterrows():
    product_name = row['Name of product']
    recall_number = row['Recall Number']
    
    print(f"Searching: {product_name}")
    
    results = search_ebay(product_name, recall_number)
    all_listings.extend(results)
    
    print(f"  Found {len(results)} listings")
    
    # wait 2 seconds between searches so we dont get blocked
    time.sleep(2)

print(f"\nTotal listings found: {len(all_listings)}")

# show first result if we found anything
if all_listings:
    print(f"\nFirst result example:")
    print(f"  Product searched: {all_listings[0]['searched_product']}")
    print(f"  Listing title: {all_listings[0]['listing_title']}")
    print(f"  Price: {all_listings[0]['price']}")
    print(f"  Condition: {all_listings[0]['condition']}")
    print(f"  URL: {all_listings[0]['url'][:80]}...")