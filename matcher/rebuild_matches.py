import pandas as pd
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np

print("Rebuilding matches table from existing data...")

conn = sqlite3.connect('data/cpsc_recalls.db')
listings = pd.read_sql("SELECT * FROM ebay_listings", conn)
recalls = pd.read_sql("SELECT * FROM recalls", conn)
clip = pd.read_sql("SELECT listing_title, clip_score FROM clip_matches", conn)
conn.close()

print(f"Listings: {len(listings)}")
print(f"Recalls: {len(recalls)}")
print(f"CLIP scores: {len(clip)}")

# load AI model
print("Loading AI model...")
model = SentenceTransformer('all-MiniLM-L6-v2')

# encode all recalled product names once
print("Encoding recalled products...")
product_names = recalls['Name of product'].tolist()
recall_embeddings = model.encode(product_names, show_progress_bar=True)

# confidence scoring function
def calculate_confidence(listing_title, recalled_product, manufacturer, similarity_score):
    score = 0
    reasons = []

    ai_points = similarity_score * 0.5
    score += ai_points
    reasons.append(f"AI similarity: +{round(ai_points, 1)} pts")

    listing_lower = listing_title.lower()
    brand_found = False

    if manufacturer:
        for word in manufacturer.lower().split():
            if len(word) > 3 and word in listing_lower:
                score += 20
                reasons.append(f"Manufacturer match '{word}': +20 pts")
                brand_found = True
                break

    if not brand_found:
        for word in recalled_product.lower().split():
            if len(word) > 3 and word in listing_lower:
                score += 20
                reasons.append(f"Brand name match '{word}': +20 pts")
                brand_found = True
                break

    stop_words = {'the', 'and', 'for', 'with', 'used', 'good', 'size',
                  'new', 'old', 'vintage', 'brand', 'model', 'inch', 'set'}
    recalled_words = set(recalled_product.lower().split()) - stop_words
    listing_words = set(listing_lower.split()) - stop_words
    overlap = recalled_words.intersection(listing_words)

    if len(recalled_words) > 0:
        overlap_pct = len(overlap) / len(recalled_words)
        overlap_points = round(overlap_pct * 20, 1)
        score += overlap_points
        reasons.append(f"Word overlap: +{overlap_points} pts")

    if recalled_product.lower() in listing_lower:
        score += 10
        reasons.append("Exact name match: +10 pts")

    return min(round(score, 1), 100), reasons

# process listings in batches of 500
BATCH_SIZE = 500
all_results = []
total = len(listings)

print(f"\nProcessing {total} listings in batches of {BATCH_SIZE}...")

for batch_start in range(0, total, BATCH_SIZE):
    batch = listings.iloc[batch_start:batch_start + BATCH_SIZE]
    titles = batch['listing_title'].tolist()

    # encode batch
    batch_embeddings = model.encode(titles)

    # compute similarity against all recalls
    similarities = cosine_similarity(batch_embeddings, recall_embeddings)

    for i, (idx, row) in enumerate(batch.iterrows()):
        # get best matching recall
        best_recall_idx = np.argmax(similarities[i])
        best_similarity = float(similarities[i][best_recall_idx]) * 100
        best_recall = recalls.iloc[best_recall_idx]

        confidence, reasons = calculate_confidence(
            row['listing_title'],
            best_recall['Name of product'],
            best_recall['Manufacturers'],
            best_similarity
        )

        verdict = 'HIGH' if confidence >= 70 else 'REVIEW' if confidence >= 50 else 'LOW'

        all_results.append({
            'listing_title': row['listing_title'],
            'searched_product': row['searched_product'],
            'recall_number': row['recall_number'],
            'recalled_product': best_recall['Name of product'],
            'manufacturer': best_recall['Manufacturers'],
            'hazard': best_recall['Hazard Description'],
            'hazard_severity': best_recall['hazard_severity'],
            'hazard_level': best_recall['hazard_level'],
            'Category': best_recall['Category'],
            'ai_similarity': round(best_similarity, 2),
            'confidence_score': confidence,
            'verdict': verdict,
            'reasons': ' | '.join(reasons),
            'price': row['price'],
            'location': row['location'],
            'url': row['url'],
            'platform': row['platform'],
            'clip_score': 0
        })

    batch_num = (batch_start // BATCH_SIZE) + 1
    total_batches = (total // BATCH_SIZE) + 1
    print(f"Batch {batch_num}/{total_batches} done — {len(all_results)} matches so far")

# merge CLIP scores
print("\nMerging CLIP scores...")
results_df = pd.DataFrame(all_results)
clip_dedup = clip.groupby('listing_title')['clip_score'].max().reset_index()
results_df = results_df.merge(clip_dedup, on='listing_title', how='left', suffixes=('', '_clip'))
results_df['clip_score'] = results_df['clip_score_clip'].fillna(0)
results_df = results_df.drop(columns=['clip_score_clip'], errors='ignore')

# apply clip bonus
def add_clip_bonus(row):
    if row['clip_score'] >= 65:
        return min(100, row['confidence_score'] + 10)
    elif row['clip_score'] >= 60:
        return min(100, row['confidence_score'] + 5)
    return row['confidence_score']

results_df['confidence_score'] = results_df.apply(add_clip_bonus, axis=1)
results_df['verdict'] = results_df['confidence_score'].apply(
    lambda x: 'HIGH' if x >= 70 else 'REVIEW' if x >= 50 else 'LOW'
)

# save to database
print("\nSaving to database...")
conn = sqlite3.connect('data/cpsc_recalls.db')
results_df.to_sql('matches', conn, if_exists='replace', index=False)
conn.close()

print(f"\n--- DONE ---")
print(f"Total matches: {len(results_df)}")
print(f"HIGH: {len(results_df[results_df['verdict'] == 'HIGH'])}")
print(f"REVIEW: {len(results_df[results_df['verdict'] == 'REVIEW'])}")
print(f"LOW: {len(results_df[results_df['verdict'] == 'LOW'])}")
print(f"\nHazard level breakdown:")
print(results_df['hazard_level'].value_counts().to_string())