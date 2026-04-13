import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

print("Starting CPSC scraper...")

# Step 1 — load the recall CSV files
recalls = pd.read_csv("data/recalls_recall_listing.csv")
warnings = pd.read_csv("data/product_safety_warning_listing.csv")

# Step 2 — lets see what we are working with
print(f"\n--- RECALLS ---")
print(f"Rows: {len(recalls)}")
print(f"Columns: {list(recalls.columns)}")

print(f"\n--- WARNINGS ---")
print(f"Rows: {len(warnings)}")
print(f"Columns: {list(warnings.columns)}")

# Step 3 — select only the columns we need
recall_cols = [
    'Recall Number',
    'Date',
    'Recall Heading',
    'Name of product',
    'Description',
    'Hazard Description',
    'Manufacturers',
    'Units'
]

warning_cols = [
    'Product Safety Warning Number',
    'Product Safety Warning Date',
    'Product Safety Warning Title',
    'Name of product',
    'Description',
    'Hazard Description',
    'Manufacturers',
    'Units'
]

recalls_clean = recalls[recall_cols].copy()
warnings_clean = warnings[warning_cols].copy()

# Step 4 — rename warning columns to match recall columns
warnings_clean = warnings_clean.rename(columns={
    'Product Safety Warning Number': 'Recall Number',
    'Product Safety Warning Date': 'Date',
    'Product Safety Warning Title': 'Recall Heading'
})

# Step 5 — add a type column so we know which is which
recalls_clean['Type'] = 'Recall'
warnings_clean['Type'] = 'Warning'

# Step 6 — combine both into one master dataframe
master = pd.concat([recalls_clean, warnings_clean], ignore_index=True)

print(f"\n--- MASTER DATABASE ---")
print(f"Total records: {len(master)}")
print(f"Columns: {list(master.columns)}")
print(f"\nFirst 3 rows:")
print(master.head(3))

# Step 7 — clean up the data
# fill any empty cells with empty string instead of NaN
master = master.fillna('')

# clean up text fields — strip extra spaces and make lowercase for easier matching later
master['Name of product'] = master['Name of product'].str.strip().str.lower()
master['Manufacturers'] = master['Manufacturers'].str.strip().str.lower()
master['Recall Heading'] = master['Recall Heading'].str.strip()

# remove any rows where product name is completely empty
master = master[master['Name of product'] != '']

print(f"Records after cleaning: {len(master)}")
print(f"\nSample product names:")
print(master['Name of product'].head(10).tolist())

# Step 8 — save to SQLite database
import sqlite3

conn = sqlite3.connect('data/cpsc_recalls.db')
master.to_sql('recalls', conn, if_exists='replace', index=False)
conn.close()

print(f"\nDatabase saved to data/cpsc_recalls.db")

# Step 9 — verify it saved correctly
conn = sqlite3.connect('data/cpsc_recalls.db')
test = pd.read_sql("SELECT COUNT(*) as total FROM recalls", conn)
conn.close()
print(f"Records in database: {test['total'][0]}")

# Step 10 — add product categories
print("\nAdding product categories...")

def categorize_product(product_name):
    product_name = product_name.lower()

    if any(word in product_name for word in [
        'baby', 'infant', 'toddler', 'child', 'kid', 'nursery', 'crib',
        'stroller', 'walker', 'bouncer', 'bassinet', 'pacifier', 'cradle',
        'playpen', 'play yard', 'high chair', 'booster', 'car seat',
        'baby monitor', 'baby gate', 'sleep sack', 'swaddle', 'teether',
        'baby carrier', 'baby swing', 'baby lounger', 'bath seat',
        'changing table', 'diaper', 'formula', 'sippy', 'bottle',
        'pediatric', 'juvenile', 'youth', 'children', 'kids'
    ]):
        return 'Baby & Children'

    elif any(word in product_name for word in [
        'bike', 'bicycle', 'helmet', 'scooter', 'skateboard', 'hoverboard',
        'trike', 'tricycle', 'kayak', 'paddle', 'ski', 'snowboard',
        'ice axe', 'climbing', 'carabiner', 'harness', 'rope', 'tent',
        'sleeping bag', 'backpack', 'hiking', 'camping gear', 'fishing',
        'hunting', 'archery', 'sports', 'athletic', 'exercise', 'fitness',
        'treadmill', 'elliptical', 'weight', 'dumbbell', 'yoga', 'gym'
    ]):
        return 'Sports & Recreation'

    elif any(word in product_name for word in [
        'dresser', 'bed', 'chair', 'table', 'sofa', 'furniture', 'mattress',
        'frame', 'couch', 'cabinet', 'bookcase', 'bookshelf', 'wardrobe',
        'armoire', 'nightstand', 'headboard', 'footboard', 'bunk',
        'loft', 'futon', 'recliner', 'ottoman', 'bench', 'stool',
        'desk', 'shelving', 'shelf', 'drawer', 'chest', 'canopy'
    ]):
        return 'Furniture'

    elif any(word in product_name for word in [
        'charger', 'battery', 'power', 'electronic', 'monitor', 'cable',
        'plug', 'outlet', 'laptop', 'computer', 'tablet', 'phone',
        'speaker', 'headphone', 'earphone', 'camera', 'tv', 'television',
        'remote', 'controller', 'switch', 'adapter', 'converter',
        'inverter', 'solar', 'generator', 'extension cord', 'surge',
        'radio', 'alarm', 'smart', 'wireless', 'bluetooth', 'usb'
    ]):
        return 'Electronics'

    elif any(word in product_name for word in [
        'pool', 'swing', 'trampoline', 'playground', 'outdoor', 'grill',
        'stove', 'camping', 'patio', 'deck', 'fence', 'gate', 'ladder',
        'lawn', 'garden', 'hose', 'sprinkler', 'mower', 'trimmer',
        'chainsaw', 'hedge', 'leaf blower', 'pressure washer', 'shed',
        'canopy tent', 'umbrella', 'hammock', 'fire pit', 'bbq',
        'barbecue', 'propane', 'butane', 'fuel', 'above ground'
    ]):
        return 'Outdoor & Garden'

    elif any(word in product_name for word in [
        'pajama', 'clothing', 'jacket', 'shirt', 'pants', 'costume',
        'hoodie', 'sweater', 'dress', 'skirt', 'shorts', 'jeans',
        'coat', 'gloves', 'hat', 'scarf', 'sock', 'shoe', 'boot',
        'sandal', 'sneaker', 'slipper', 'apparel', 'uniform', 'vest',
        'swimsuit', 'bikini', 'leggings', 'underwear', 'nightgown'
    ]):
        return 'Clothing'

    elif any(word in product_name for word in [
        'toy', 'game', 'puzzle', 'doll', 'magnet', 'fidget', 'lego',
        'block', 'marble', 'ball', 'kite', 'yo-yo', 'action figure',
        'stuffed', 'plush', 'board game', 'card game', 'craft',
        'art set', 'paint', 'clay', 'slime', 'kinetic', 'sand',
        'water gun', 'foam', 'nerf', 'remote control', 'rc car',
        'drone', 'robot', 'science kit', 'building set', 'train set'
    ]):
        return 'Toys & Games'

    elif any(word in product_name for word in [
        'serum', 'cream', 'lotion', 'spray', 'hair', 'skin', 'beauty',
        'minoxidil', 'shampoo', 'conditioner', 'makeup', 'cosmetic',
        'lipstick', 'mascara', 'foundation', 'blush', 'eyeshadow',
        'nail', 'perfume', 'cologne', 'deodorant', 'sunscreen',
        'moisturizer', 'toner', 'cleanser', 'scrub', 'mask',
        'supplement', 'vitamin', 'probiotic', 'protein powder',
        'weight loss', 'detox', 'essential oil', 'beard', 'growth'
    ]):
        return 'Health & Beauty'

    elif any(word in product_name for word in [
        'steamer', 'blender', 'cooker', 'fryer', 'appliance', 'vacuum',
        'washer', 'dryer', 'dishwasher', 'refrigerator', 'freezer',
        'microwave', 'toaster', 'coffee', 'espresso', 'juicer',
        'mixer', 'food processor', 'instant pot', 'air fryer',
        'rice cooker', 'slow cooker', 'pressure cooker', 'griddle',
        'waffle', 'sandwich', 'panini', 'kettle', 'water heater',
        'humidifier', 'dehumidifier', 'air purifier', 'fan', 'heater',
        'iron', 'sewing', 'knitting', 'pan', 'skillet', 'cookware'
    ]):
        return 'Home Appliances'

    elif any(word in product_name for word in [
        'ladder', 'tool', 'saw', 'drill', 'planer', 'hardware',
        'screwdriver', 'wrench', 'hammer', 'nail gun', 'staple gun',
        'sander', 'grinder', 'router', 'jigsaw', 'circular saw',
        'table saw', 'miter saw', 'band saw', 'lathe', 'press',
        'welder', 'torch', 'compressor', 'generator', 'jack',
        'hoist', 'winch', 'cable', 'wire', 'pipe', 'fitting'
    ]):
        return 'Tools & Hardware'

    elif any(word in product_name for word in [
        'bed rail', 'rail', 'walker', 'wheelchair', 'cane', 'crutch',
        'brace', 'bandage', 'first aid', 'thermometer', 'blood pressure',
        'pulse', 'glucose', 'medical', 'surgical', 'hospital',
        'mobility', 'lift', 'grab bar', 'bath bench', 'shower chair'
    ]):
        return 'Medical & Mobility'

    else:
        return 'Other'

# apply categories to master dataframe
conn = sqlite3.connect('data/cpsc_recalls.db')
master = pd.read_sql("SELECT * FROM recalls", conn)

master['Category'] = master['Name of product'].apply(categorize_product)

# save back to database
master.to_sql('recalls', conn, if_exists='replace', index=False)
conn.close()

# show category breakdown
print(master['Category'].value_counts().to_string())
print(f"\nCategories added to database!")