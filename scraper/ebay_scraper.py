import requests
import pandas as pd
import sqlite3
import time
import os
import base64
from dotenv import load_dotenv

load_dotenv()
APP_ID = os.getenv('EBAY_APP_ID')
CERT_ID = os.getenv('EBAY_CERT_ID')

print("Starting eBay scraper...")
print(f"App ID loaded: {APP_ID[:15]}...")
print(f"Cert ID loaded: {CERT_ID[:15]}...")

# Step 1 — load recall database
conn = sqlite3.connect('data/cpsc_recalls.db')
recalls = pd.read_sql("SELECT * FROM recalls", conn)
conn.close()

print(f"Loaded {len(recalls)} recalled products")


# Step 2 — get OAuth token using App ID + Cert ID
def get_oauth_token():
    url = "https://api.ebay.com/identity/v1/oauth2/token"

    # combine App ID and Cert ID into a base64 encoded credential
    credentials = f"{APP_ID}:{CERT_ID}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }

    try:
        response = requests.post(url, headers=headers, data=data)

        if response.status_code == 200:
            token = response.json()['access_token']
            print("OAuth token obtained successfully!")
            return token
        else:
            print(f"Token error: {response.status_code}")
            print(f"Response: {response.text[:300]}")
            return None

    except Exception as e:
        print(f"Token exception: {e}")
        return None


# Step 3 — search eBay using Browse API
def search_ebay(product_name, recall_number, token, max_results=10):

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "Content-Type": "application/json"
    }

    params = {
        "q": product_name,
        "limit": max_results,
        "filter": "conditions:{USED}",
        "sort": "bestMatch"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)

        if response.status_code != 200:
            print(f"  Error {response.status_code} for {product_name}")
            print(f"  Response: {response.text[:300]}")
            return []

        data = response.json()
        items = data.get('itemSummaries', [])

        results = []
        for item in items:
            title = item.get('title', '')
            price = item.get('price', {}).get('value', 'N/A')
            currency = item.get('price', {}).get('currency', 'USD')
            url_item = item.get('itemWebUrl', '')
            condition = item.get('condition', 'Unknown')
            location = item.get('itemLocation', {}).get('country', 'Unknown')

            # get image URL directly from API response
            image_url = ''
            thumbnails = item.get('thumbnailImages', [])
            if thumbnails:
                image_url = thumbnails[0].get('imageUrl', '')
            if not image_url:
                image_url = item.get('image', {}).get('imageUrl', '')

            results.append({
                'recall_number': recall_number,
                'searched_product': product_name,
                'listing_title': title,
                'price': f"{currency} {price}",
                'condition': condition,
                'location': location,
                'url': url_item,
                'image_url': image_url,
                'platform': 'eBay'
            })

        return results

    except Exception as e:
        print(f"  Exception for {product_name}: {e}")
        return []


# Step 4 — get token first then test on 5 products
print("\nGetting OAuth token...")
token = get_oauth_token()

if not token:
    print("Could not get token. Check your App ID and Cert ID.")
else:
    print("\nTesting on 5 products...")

    test_recalls = recalls.head(5)
    all_listings = []

    for index, row in test_recalls.iterrows():
        product_name = row['Name of product']
        recall_number = row['Recall Number']

        print(f"Searching: {product_name}")
        results = search_ebay(product_name, recall_number, token)
        all_listings.extend(results)
        print(f"  Found {len(results)} listings")

        time.sleep(2)

    print(f"\nTotal listings found: {len(all_listings)}")

    if all_listings:
        print(f"\nFirst result:")
        print(f"  Title:     {all_listings[0]['listing_title']}")
        print(f"  Price:     {all_listings[0]['price']}")
        print(f"  Condition: {all_listings[0]['condition']}")
        print(f"  Location:  {all_listings[0]['location']}")
        print(f"  URL:       {all_listings[0]['url'][:80]}...")

        # Step 5 — run on 50 products and save results to database
    print("\nRunning on 50 products...")

    all_listings = []
    found_count = 0

    for index, row in recalls.head(200).iterrows():
        product_name = row['Name of product']
        recall_number = row['Recall Number']

        results = search_ebay(product_name, recall_number, token)

        if results:
            found_count += 1
            print(f"FOUND {len(results)} listings for: {product_name}")
            all_listings.extend(results)

        time.sleep(2)

    print(f"\n--- RESULTS ---")
    print(f"Products searched: 50")
    print(f"Products with listings found: {found_count}")
    print(f"Total listings collected: {len(all_listings)}")

    # Step 6 — save to database
    if all_listings:
        listings_df = pd.DataFrame(all_listings)
        conn = sqlite3.connect('data/cpsc_recalls.db')
        listings_df.to_sql('ebay_listings', conn, if_exists='replace', index=False)
        conn.close()
        print(f"Saved {len(all_listings)} listings to database")