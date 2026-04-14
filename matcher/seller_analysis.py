import pandas as pd
import sqlite3

print("Running seller analysis...")

# Step 1 — load eBay listings with seller data
conn = sqlite3.connect('data/cpsc_recalls.db')
listings = pd.read_sql(
    "SELECT * FROM ebay_listings WHERE platform = 'eBay' AND seller_username != 'unknown'",
    conn
)
matches = pd.read_sql("SELECT * FROM matches", conn)
conn.close()

print(f"Loaded {len(listings)} eBay listings with seller data")

# Step 2 — join listings with match verdicts
listings_with_verdicts = listings.merge(
    matches[['listing_title', 'confidence_score', 'verdict', 'recalled_product']],
    on='listing_title',
    how='left'
)

# only keep flagged listings
flagged = listings_with_verdicts[
    listings_with_verdicts['verdict'].isin(['HIGH', 'REVIEW'])
].copy()

print(f"Flagged listings with seller data: {len(flagged)}")

# Step 3 — aggregate by seller
seller_stats = flagged.groupby('seller_username').agg(
    total_flagged=('listing_title', 'count'),
    high_confidence=('verdict', lambda x: (x == 'HIGH').sum()),
    review_confidence=('verdict', lambda x: (x == 'REVIEW').sum()),
    avg_confidence=('confidence_score', 'mean'),
    max_confidence=('confidence_score', 'max'),
    feedback_score=('seller_feedback', 'first'),
    feedback_pct=('seller_feedback_pct', 'first'),
    recalled_products=('recalled_product', lambda x: ', '.join(x.unique()[:3]))
).reset_index()

# add direct eBay profile link
seller_stats['ebay_profile'] = seller_stats['seller_username'].apply(
    lambda x: f"https://www.ebay.com/usr/{x}"
)

# Step 4 — classify sellers by risk level
def seller_risk(row):
    if row['high_confidence'] >= 2:
        return 'HIGH RISK'
    elif row['high_confidence'] >= 1 or row['total_flagged'] >= 3:
        return 'MEDIUM RISK'
    else:
        return 'LOW RISK'

seller_stats['risk_level'] = seller_stats.apply(seller_risk, axis=1)

# sort by most flagged first
seller_stats = seller_stats.sort_values(
    ['high_confidence', 'total_flagged'],
    ascending=False
)

# Step 5 — save to database
conn = sqlite3.connect('data/cpsc_recalls.db')
seller_stats.to_sql('seller_flags', conn, if_exists='replace', index=False)
conn.close()

print(f"\n--- SELLER ANALYSIS RESULTS ---")
print(f"Total unique sellers flagged: {len(seller_stats)}")
print(f"HIGH RISK sellers: {len(seller_stats[seller_stats['risk_level'] == 'HIGH RISK'])}")
print(f"MEDIUM RISK sellers: {len(seller_stats[seller_stats['risk_level'] == 'MEDIUM RISK'])}")
print(f"LOW RISK sellers: {len(seller_stats[seller_stats['risk_level'] == 'LOW RISK'])}")

print(f"\nTop 10 sellers by flagged listings:")
print(seller_stats[[
    'seller_username', 'total_flagged', 'high_confidence',
    'risk_level', 'feedback_score', 'recalled_products'
]].head(10).to_string())