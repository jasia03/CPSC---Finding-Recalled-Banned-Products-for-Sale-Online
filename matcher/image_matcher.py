import requests
import sqlite3
import pandas as pd
import torch
import clip
from PIL import Image
from io import BytesIO
import time

print("Loading CLIP model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)
print(f"CLIP model loaded on {device}")

# Step 1 — load listings with image URLs
conn = sqlite3.connect('data/cpsc_recalls.db')
listings = pd.read_sql(
    "SELECT * FROM ebay_listings WHERE image_url != '' AND image_url IS NOT NULL",
    conn
)
recalls = pd.read_sql("SELECT * FROM recalls", conn)
conn.close()

print(f"Loaded {len(listings)} listings with images")


# Step 2 — download image from URL
def get_image(image_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(image_url, headers=headers, timeout=10)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content)).convert('RGB')
            return image
        return None
    except Exception as e:
        return None


# Step 3 — CLIP similarity between image and text
def clip_similarity(image, text_description):
    try:
        image_input = preprocess(image).unsqueeze(0).to(device)
        text_input = clip.tokenize([text_description], truncate=True).to(device)

        with torch.no_grad():
            image_features = model.encode_image(image_input)
            text_features = model.encode_text(text_input)

        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)

        similarity = (image_features @ text_features.T).item()
        score = round((similarity + 1) / 2 * 100, 2)
        return score

    except Exception as e:
        return 0.0


# Step 4 — run CLIP on listings with images
print("\nRunning CLIP image matching...")

results = []
tested = 0
max_test = 30

for index, row in listings.head(max_test).iterrows():
    image_url = row['image_url']
    recall_number = row['recall_number']
    listing_title = row['listing_title']
    searched_product = row['searched_product']

    # get recalled product info
    recall_row = recalls[recalls['Recall Number'] == recall_number]
    if recall_row.empty:
        continue

    hazard = recall_row.iloc[0]['Hazard Description']
    product_name = recall_row.iloc[0]['Name of product']
    text_query = f"recalled product: {product_name}. hazard: {hazard}"

    # download image
    image = get_image(image_url)

    if image is None:
        print(f"  Could not load image for: {listing_title[:40]}")
        continue

    # run CLIP
    score = clip_similarity(image, text_query)
    print(f"  {score}% — {listing_title[:50]}")

    results.append({
        'listing_title': listing_title,
        'searched_product': searched_product,
        'recall_number': recall_number,
        'clip_score': score,
        'image_url': image_url
    })

    tested += 1
    time.sleep(0.5)

# Step 5 — show and save results
print(f"\n--- CLIP RESULTS ---")
print(f"Listings tested: {tested}")

if results:
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values('clip_score', ascending=False)

    print("\nTop matches by CLIP score:")
    print(results_df[['listing_title', 'clip_score']].head(10).to_string())

    # save to database
    conn = sqlite3.connect('data/cpsc_recalls.db')
    results_df.to_sql('clip_matches', conn, if_exists='replace', index=False)
    conn.close()
    print(f"\nSaved {len(results_df)} CLIP results to database")