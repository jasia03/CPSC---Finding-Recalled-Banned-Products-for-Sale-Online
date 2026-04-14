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

# Step 1 — load listings that have image URLs
conn = sqlite3.connect('data/cpsc_recalls.db')
listings = pd.read_sql(
    "SELECT * FROM ebay_listings WHERE image_url != '' AND image_url IS NOT NULL",
    conn
)
recalls = pd.read_sql("SELECT * FROM recalls", conn)

# check which listings already have CLIP scores
try:
    existing_clips = pd.read_sql("SELECT listing_title FROM clip_matches", conn)
    already_done = set(existing_clips['listing_title'].tolist())
    print(f"Already have CLIP scores for {len(already_done)} listings")
except:
    already_done = set()
    print("No existing CLIP scores found")

conn.close()

# filter to only listings without CLIP scores yet
listings_todo = listings[~listings['listing_title'].isin(already_done)]
print(f"Listings with images: {len(listings)}")
print(f"Listings still to process: {len(listings_todo)}")


# Step 2 — download image
def get_image(image_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(image_url, headers=headers, timeout=8)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content)).convert('RGB')
            return image
        return None
    except:
        return None


# Step 3 — CLIP similarity
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
    except:
        return 0.0


# Step 4 — process in batches of 100 and save after each batch
BATCH_SIZE = 100
total_processed = 0
total_saved = 0

print(f"\nProcessing in batches of {BATCH_SIZE}...")
print("Progress saves after every batch so you can stop and resume safely\n")

for batch_start in range(0, len(listings_todo), BATCH_SIZE):
    batch = listings_todo.iloc[batch_start:batch_start + BATCH_SIZE]
    batch_results = []

    for index, row in batch.iterrows():
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

        # download and score image
        image = get_image(image_url)
        if image is None:
            continue

        score = clip_similarity(image, text_query)
        batch_results.append({
            'listing_title': listing_title,
            'searched_product': searched_product,
            'recall_number': recall_number,
            'clip_score': score,
            'image_url': image_url
        })

        total_processed += 1
        time.sleep(0.3)

    # save batch to database
    if batch_results:
        batch_df = pd.DataFrame(batch_results)
        conn = sqlite3.connect('data/cpsc_recalls.db')
        batch_df.to_sql('clip_matches', conn,
                        if_exists='append',
                        index=False)
        conn.close()
        total_saved += len(batch_results)

    batch_num = (batch_start // BATCH_SIZE) + 1
    total_batches = (len(listings_todo) // BATCH_SIZE) + 1
    print(f"Batch {batch_num}/{total_batches} done — {total_saved} CLIP scores saved so far")


# Step 5 — merge all CLIP scores into matches table
print(f"\n--- FINISHED ---")
print(f"Total listings processed: {total_processed}")
print(f"Total CLIP scores saved: {total_saved}")
print("\nMerging CLIP scores into matches table...")

conn = sqlite3.connect('data/cpsc_recalls.db')
matches_df = pd.read_sql("SELECT * FROM matches", conn)
clip_df = pd.read_sql(
    "SELECT listing_title, clip_score, image_url FROM clip_matches",
    conn
)
conn.close()

# keep best CLIP score per listing title
clip_df = clip_df.groupby('listing_title').agg(
    clip_score=('clip_score', 'max'),
    image_url=('image_url', 'first')
).reset_index()

if 'clip_score_y' in merged.columns:
    merged['clip_score'] = merged['clip_score_y'].fillna(0)
elif 'clip_score' not in merged.columns:
    merged['clip_score'] = 0

if 'image_url_y' in merged.columns:
    merged['image_url'] = merged['image_url_y'].fillna('')
elif 'image_url' not in merged.columns:
    merged['image_url'] = ''

merged['clip_score'] = merged['clip_score'].fillna(0)
merged['image_url'] = merged['image_url'].fillna('')
# add clip bonus to confidence score
def add_clip_bonus(row):
    if row['clip_score'] >= 65:
        return min(100, row['confidence_score'] + 10)
    elif row['clip_score'] >= 60:
        return min(100, row['confidence_score'] + 5)
    return row['confidence_score']

merged['confidence_score'] = merged.apply(add_clip_bonus, axis=1)

def update_verdict(score):
    if score >= 70:
        return 'HIGH'
    elif score >= 50:
        return 'REVIEW'
    return 'LOW'

merged['verdict'] = merged['confidence_score'].apply(update_verdict)

conn = sqlite3.connect('data/cpsc_recalls.db')
merged.to_sql('matches', conn, if_exists='replace', index=False)
conn.close()

print(f"Updated {len(merged)} matches with CLIP scores")
print(f"HIGH confidence: {len(merged[merged['verdict'] == 'HIGH'])}")
print(f"REVIEW: {len(merged[merged['verdict'] == 'REVIEW'])}")