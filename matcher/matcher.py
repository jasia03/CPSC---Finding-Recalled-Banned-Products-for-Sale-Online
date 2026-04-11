import pandas as pd
import sqlite3
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np

print("Loading matching engine...")

# Step 1 — load our recall database
conn = sqlite3.connect('data/cpsc_recalls.db')
recalls = pd.read_sql("SELECT * FROM recalls", conn)
conn.close()

print(f"Loaded {len(recalls)} recalled products")

# Step 2 — load the AI model
# this model converts text into numbers (embeddings)
# so we can measure how similar two pieces of text are mathematically
print("Loading AI model... (this may take a minute first time)")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("AI model ready!")

# Step 3 — create embeddings for all recalled product names
# this converts every product name in our database into numbers
# we do this once and reuse it for every comparison
print("\nConverting recalled products to embeddings...")
print("This may take a minute for 9000+ products...")

product_names = recalls['Name of product'].tolist()
recall_embeddings = model.encode(product_names, show_progress_bar=True)

print(f"Created embeddings for {len(recall_embeddings)} products")
print(f"Each embedding is {len(recall_embeddings[0])} numbers")

# Step 4 — the matching function
# this takes one listing title and finds the most similar recalled products
def match_listing(listing_title, top_n=5):
    
    # convert the listing title into embeddings too
    listing_embedding = model.encode([listing_title])
    
    # compare the listing against every recalled product mathematically
    similarities = cosine_similarity(listing_embedding, recall_embeddings)[0]
    
    # get the top N most similar recalled products
    top_indices = np.argsort(similarities)[::-1][:top_n]
    
    matches = []
    for idx in top_indices:
        matches.append({
            'recall_number': recalls.iloc[idx]['Recall Number'],
            'recalled_product': recalls.iloc[idx]['Name of product'],
            'manufacturer': recalls.iloc[idx]['Manufacturers'],
            'hazard': recalls.iloc[idx]['Hazard Description'],
            'similarity_score': round(float(similarities[idx]) * 100, 2)
        })
    
    return matches


# Step 5 — test it with some fake listings
print("\nTesting matcher with sample listings...")

test_listings = [
    "Fisher Price baby swing infant rocker used",
    "Graco car seat infant used good condition",
    "iPhone 15 Pro Max 256GB unlocked",
    "vintage canopy bed frame queen size",
    "hair growth serum minoxidil 5% bottles"
]

for listing in test_listings:
    print(f"\nListing: '{listing}'")
    print(f"Top matches:")
    matches = match_listing(listing)
    for match in matches[:3]:
        print(f"  {match['similarity_score']}% — {match['recalled_product']}")


# Step 6 — confidence scoring system
# combines multiple signals into one score from 0-100
def calculate_confidence(listing_title, recalled_product, manufacturer, similarity_score):
    
    score = 0
    reasons = []
    
    # Signal 1 — AI similarity score (max 50 points)
    # similarity score is already 0-100, we give it half weight
    ai_points = similarity_score * 0.5
    score += ai_points
    reasons.append(f"AI similarity: +{round(ai_points, 1)} pts")
    
    # Signal 2 — brand name appears in listing (max 20 points)
    # check manufacturer field AND product name for brand words
    listing_lower = listing_title.lower()
    brand_found = False
    
    # check manufacturer field first
    if manufacturer:
        manufacturer_words = manufacturer.lower().split()
        for word in manufacturer_words:
            if len(word) > 3 and word in listing_lower:
                score += 20
                reasons.append(f"Manufacturer match '{word}': +20 pts")
                brand_found = True
                break
    
    # also check product name words as brand signals
    if not brand_found:
        product_words = recalled_product.lower().split()
        for word in product_words:
            # first meaningful word is usually the brand name
            if len(word) > 3 and word in listing_lower:
                score += 20
                reasons.append(f"Brand name match '{word}': +20 pts")
                brand_found = True
                break
    
    # Signal 3 — key product words overlap (max 20 points)
    recalled_words = set(recalled_product.lower().split())
    listing_words = set(listing_title.lower().split())
    # remove common words that dont help matching
    stop_words = {'the', 'and', 'for', 'with', 'used', 'good', 'size', 
                  'new', 'old', 'vintage', 'brand', 'model', 'inch', 'set'}
    recalled_words = recalled_words - stop_words
    listing_words = listing_words - stop_words
    
    overlap = recalled_words.intersection(listing_words)
    if len(recalled_words) > 0:
        overlap_pct = len(overlap) / len(recalled_words)
        overlap_points = round(overlap_pct * 20, 1)
        score += overlap_points
        reasons.append(f"Word overlap {len(overlap)}/{len(recalled_words)} words: +{overlap_points} pts")
    
    # Signal 4 — exact product name appears in listing (bonus 10 points)
    if recalled_product.lower() in listing_title.lower():
        score += 10
        reasons.append(f"Exact name match: +10 pts")
    
    # cap score at 100
    final_score = min(round(score, 1), 100)
    
    return final_score, reasons


# Step 7 — full pipeline combining matcher + confidence score
def analyze_listing(listing_title):
    
    # get top AI matches
    matches = match_listing(listing_title, top_n=3)
    
    results = []
    for match in matches:
        confidence, reasons = calculate_confidence(
            listing_title,
            match['recalled_product'],
            match['manufacturer'],
            match['similarity_score']
        )
        
        results.append({
            'listing_title': listing_title,
            'recalled_product': match['recalled_product'],
            'manufacturer': match['manufacturer'],
            'hazard': match['hazard'],
            'recall_number': match['recall_number'],
            'ai_similarity': match['similarity_score'],
            'confidence_score': confidence,
            'reasons': reasons,
            'verdict': 'HIGH' if confidence >= 70 else 'REVIEW' if confidence >= 50 else 'LOW'
        })
    
    # return the best match only
    results.sort(key=lambda x: x['confidence_score'], reverse=True)
    return results[0] if results else None


# Step 8 — test the full pipeline
print("\n--- FULL PIPELINE TEST ---")

test_listings = [
    "Fisher Price baby swing infant rocker used",
    "Graco car seat infant used good condition",
    "iPhone 15 Pro Max 256GB unlocked",
    "vintage canopy bed frame queen size",
    "hair growth serum minoxidil 5% bottles",
    "htrc battery charger for rc cars",
    "sangohe bed rail for adults portable"
]

for listing in test_listings:
    result = analyze_listing(listing)
    if result:
        print(f"\nListing: '{listing}'")
        print(f"Best match: {result['recalled_product']}")
        print(f"Confidence: {result['confidence_score']}% — {result['verdict']}")
        print(f"Hazard: {result['hazard'][:80]}")
        print(f"Scoring breakdown: {result['reasons']}")

        # Step 9 — save matcher results to SQLite
# in real use this will process actual eBay listings
# for now we save our test results to confirm the pipeline works

print("\n--- SAVING RESULTS TO DATABASE ---")

# create a list of results from our test listings
final_results = []
for listing in test_listings:
    result = analyze_listing(listing)
    if result:
        final_results.append(result)

# convert to dataframe
results_df = pd.DataFrame(final_results)

# drop the reasons column for storage (it's a list, hard to store in SQL)
results_df['reasons'] = results_df['reasons'].apply(lambda x: ' | '.join(x))

# save to database
conn = sqlite3.connect('data/cpsc_recalls.db')
results_df.to_sql('matches', conn, if_exists='replace', index=False)
conn.close()

print(f"Saved {len(results_df)} matches to database")

# verify
conn = sqlite3.connect('data/cpsc_recalls.db')
saved = pd.read_sql("SELECT listing_title, recalled_product, confidence_score, verdict FROM matches ORDER BY confidence_score DESC", conn)
conn.close()

print("\nSaved matches:")
print(saved.to_string())

# Step 10 — run matcher on real eBay listings
print("\n--- RUNNING MATCHER ON REAL EBAY LISTINGS ---")

# load the real ebay listings
conn = sqlite3.connect('data/cpsc_recalls.db')
ebay_listings = pd.read_sql("SELECT * FROM ebay_listings", conn)
conn.close()

print(f"Loaded {len(ebay_listings)} real eBay listings")

real_results = []

for index, row in ebay_listings.iterrows():
    listing_title = row['listing_title']
    result = analyze_listing(listing_title)

    if result:
        # add the eBay listing details to the result
        result['price'] = row['price']
        result['location'] = row['location']
        result['url'] = row['url']
        result['platform'] = row['platform']
        result['searched_product'] = row['searched_product']
        real_results.append(result)

print(f"Analyzed {len(real_results)} listings")

# save to database
real_df = pd.DataFrame(real_results)

# add category from recalls database
conn = sqlite3.connect('data/cpsc_recalls.db')
recalls_with_cat = pd.read_sql("SELECT [Recall Number], Category FROM recalls", conn)
conn.close()

real_df = real_df.merge(
    recalls_with_cat,
    left_on='recall_number',
    right_on='Recall Number',
    how='left'
)
real_df['Category'] = real_df['Category'].fillna('Other')


real_df['reasons'] = real_df['reasons'].apply(lambda x: ' | '.join(x))

conn = sqlite3.connect('data/cpsc_recalls.db')
real_df.to_sql('matches', conn, if_exists='replace', index=False)
conn.close()

print(f"Saved {len(real_df)} matches to database")

# show top 10 highest confidence matches
print("\nTop 10 highest confidence matches:")
top = real_df.nlargest(10, 'confidence_score')[
    ['listing_title', 'recalled_product', 'confidence_score', 'verdict', 'price']
]
print(top.to_string())