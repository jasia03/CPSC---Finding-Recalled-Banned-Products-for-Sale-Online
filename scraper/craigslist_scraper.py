import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import time
import json
import re

print("Starting Craigslist scraper...")

# Step 1 — load recall database
conn = sqlite3.connect('data/cpsc_recalls.db')
recalls = pd.read_sql("SELECT * FROM recalls", conn)
conn.close()

print(f"Loaded {len(recalls)} recalled products")

# extract short search term for craigslist
# craigslist works best with 2-3 word queries not full product names
def get_search_term(product_name):
    # generic product type keywords by category
    # these are the terms real people use on craigslist
    generic_terms = {
        'walker': 'baby walker',
        'bed rail': 'bed rail',
        'dresser': 'dresser',
        'crib': 'crib',
        'stroller': 'stroller',
        'car seat': 'car seat',
        'high chair': 'high chair',
        'play yard': 'play yard',
        'swing': 'baby swing',
        'bouncer': 'baby bouncer',
        'baby monitor': 'baby monitor',
        'pool': 'above ground pool',
        'trampoline': 'trampoline',
        'bike': 'bicycle',
        'helmet': 'helmet',
        'scooter': 'scooter',
        'hoverboard': 'hoverboard',
        'treadmill': 'treadmill',
        'charger': 'battery charger',
        'steamer': 'steamer',
        'grill': 'grill',
        'ladder': 'ladder',
        'dresser': 'dresser',
        'canopy': 'canopy bed',
        'minoxidil': 'minoxidil',
        'hair growth': 'hair growth serum',
        'pajama': 'pajamas',
        'toy': 'toy',
        'bath seat': 'baby bath seat',
        'bed frame': 'bed frame',
        'office chair': 'office chair',
        'air fryer': 'air fryer',
        'fan': 'fan',
        'heater': 'heater',
        'pan': 'frying pan',
        'skillet': 'skillet',
        'power bank': 'power bank',
        'ice axe': 'ice axe',
        'carabiner': 'carabiner',
        'camping stove': 'camping stove',
    }

    product_lower = product_name.lower()

    # check if any generic term matches the product name
    for keyword, search_term in generic_terms.items():
        if keyword in product_lower:
            return search_term

    # fallback — use first 2 meaningful words
    stop_words = {
        'brand', 'model', 'type', 'series', 'and', 'the', 'for',
        'with', 'by', 'of', 'in', 'a', 'an', 'inch', 'size',
        'pack', 'set', 'kit', 'heavy', 'duty', 'portable', 'adult'
    }
    words = product_name.lower().split()
    meaningful = [w for w in words if w not in stop_words and len(w) > 3]
    return ' '.join(meaningful[:2])

CITIES = [
    'newyork',
    'losangeles',
    'chicago',
    'houston',
    'phoenix',
    'philadelphia',
    'dallas',
    'sfbay',
    'seattle',
    'miami'
]

# Step 2 — search craigslist using JSON data in page source
def search_craigslist(product_name, recall_number, city):

    short_term = get_search_term(product_name)
    search_query = short_term.replace(' ', '%20')
    url = f"https://{city}.craigslist.org/search/sss?query={search_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')

        # find the JSON data embedded in the page
        json_tag = soup.find('script', id='ld_searchpage_results')

        if not json_tag:
            return []

        data = json.loads(json_tag.string)
        items = data.get('itemListElement', [])

        results = []
        for item in items:
            listing = item.get('item', {})

            title = listing.get('name', '')
            url_item = listing.get('url', '')
            price = listing.get('offers', {}).get('price', 'N/A')
            currency = listing.get('offers', {}).get('priceCurrency', 'USD')
            location = listing.get('offers', {}).get('availableAtOrFrom', {}).get('name', city)
            images = listing.get('image', [])
            image_url = images[0] if images else ''

            if title:
                price_str = f"{currency} {price}" if price != 'N/A' else 'N/A'
                results.append({
                    'recall_number': recall_number,
                    'searched_product': product_name,
                    'listing_title': title,
                    'price': price_str,
                    'condition': 'Used',
                    'location': location,
                    'url': url_item,
                    'image_url': image_url,
                    'platform': 'Craigslist'
                })

        return results

    except Exception as e:
        print(f"  Error: {e}")
        return []


# Step 3 — test on 5 products across 3 cities
print("\nTesting on 5 products across 3 cities...")

test_recalls = recalls.head(5)
all_listings = []

for index, row in test_recalls.iterrows():
    product_name = row['Name of product']
    recall_number = row['Recall Number']

    short_term = get_search_term(product_name)
    print(f"Searching: '{product_name}'")
    print(f"  Using search term: '{short_term}'")

    for city in CITIES[:3]:
        results = search_craigslist(product_name, recall_number, city)
        all_listings.extend(results)
        time.sleep(1)

    print(f"  Found {len(all_listings)} listings so far")

print(f"\nTotal listings found: {len(all_listings)}")

if all_listings:
    print(f"\nFirst result:")
    print(f"  Title:    {all_listings[0]['listing_title']}")
    print(f"  Price:    {all_listings[0]['price']}")
    print(f"  Location: {all_listings[0]['location']}")
    print(f"  URL:      {all_listings[0]['url'][:80]}...")


# Step 4 — run on 50 products across all 10 cities and save
print("\nRunning full scrape on 50 products across all cities...")
print("This will take several minutes...")

all_listings = []
found_count = 0

for index, row in recalls.head(50).iterrows():
    product_name = row['Name of product']
    recall_number = row['Recall Number']
    short_term = get_search_term(product_name)

    city_results = []
    for city in CITIES:
        results = search_craigslist(product_name, recall_number, city)
        city_results.extend(results)
        time.sleep(0.5)

    if city_results:
        found_count += 1
        print(f"FOUND {len(city_results)} listings for: {short_term}")
        all_listings.extend(city_results)

    time.sleep(1)

print(f"\n--- CRAIGSLIST RESULTS ---")
print(f"Products searched: 50")
print(f"Products with listings: {found_count}")
print(f"Total listings collected: {len(all_listings)}")

# Step 5 — save to database alongside eBay listings
if all_listings:
    listings_df = pd.DataFrame(all_listings)

    conn = sqlite3.connect('data/cpsc_recalls.db')

    # append to existing ebay listings
    existing = pd.read_sql("SELECT * FROM ebay_listings", conn)
    combined = pd.concat([existing, listings_df], ignore_index=True)
    combined.to_sql('ebay_listings', conn, if_exists='replace', index=False)
    conn.close()

    print(f"\nTotal listings in database: {len(combined)}")
    print(f"eBay: {len(existing)}")
    print(f"Craigslist: {len(listings_df)}")


# Step 6 — pre-filter obvious noise before AI matching
print("\nPre-filtering listings...")

conn = sqlite3.connect('data/cpsc_recalls.db')
all_data = pd.read_sql("SELECT * FROM ebay_listings", conn)
recalls_db = pd.read_sql("SELECT [Recall Number], [Name of product] FROM recalls", conn)
conn.close()

def is_relevant(listing_title, searched_product):
    # get meaningful words from the recalled product name
    stop_words = {
        'and', 'the', 'for', 'with', 'by', 'of', 'in', 'a', 'an',
        'brand', 'model', 'type', 'series', 'inch', 'size', 'pack',
        'set', 'kit', 'heavy', 'duty', 'portable', 'adult', 'children'
    }
    product_words = [
        w for w in searched_product.lower().split()
        if w not in stop_words and len(w) > 3
    ]
    listing_lower = listing_title.lower()

    # keep listing if any meaningful product word appears in title
    return any(word in listing_lower for word in product_words)

# apply filter to craigslist listings only
craigslist_mask = all_data['platform'] == 'Craigslist'
craigslist_data = all_data[craigslist_mask].copy()
ebay_data = all_data[~craigslist_mask].copy()

craigslist_data['relevant'] = craigslist_data.apply(
    lambda row: is_relevant(row['listing_title'], row['searched_product']),
    axis=1
)

filtered_craigslist = craigslist_data[craigslist_data['relevant']].drop('relevant', axis=1)

print(f"Craigslist before filter: {len(craigslist_data)}")
print(f"Craigslist after filter:  {len(filtered_craigslist)}")
print(f"eBay listings kept:       {len(ebay_data)}")

# combine filtered craigslist with ebay
final_combined = pd.concat([ebay_data, filtered_craigslist], ignore_index=True)
print(f"Total for AI matching:    {len(final_combined)}")

# save filtered combined dataset
conn = sqlite3.connect('data/cpsc_recalls.db')
final_combined.to_sql('ebay_listings', conn, if_exists='replace', index=False)
conn.close()

print("\nFiltered dataset saved — ready for AI matching!")