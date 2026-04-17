# CPSC Recall Finder
### Challenge X

An automated system that identifies recalled and banned consumer products listed for sale on consumer-to-consumer (C2C) online platforms using AI-powered matching, image recognition, and a live review dashboard.

---

## Live Demo
🔗 [View the live dashboard here](https://cpsc---finding-recalled-banned-appucts-for-sale-online-amzepch.streamlit.app/)

---

## Results
- **9,318** recalled products loaded from CPSC database
- **26,365** listings flagged across eBay and Craigslist
- **4,849** HIGH confidence matches
- **320** unique sellers flagged — 26 HIGH RISK repeat offenders
- Baby walkers (federally banned) found selling for $15–$40
- Infant walkers, bed rails, baby bath seats, pools all flagged
- 10 US cities covered on Craigslist

---

## The Problem
The U.S. Consumer Product Safety Commission (CPSC) currently monitors C2C platforms manually to find recalled products still being sold. This is slow, inefficient, and means dangerous products stay listed longer than they should.

## Our Solution
An end-to-end automated pipeline that:
1. Loads all CPSC recalled and banned products into a database
2. Searches eBay and Craigslist for listings matching those products
3. Uses AI to score each listing's likelihood of being a recalled product
4. Flags repeat offending sellers for enforcement action
5. Presents everything in a live dashboard for human review

---

## How It Works

### Matching Engine — 4 Layers
**Layer 1 — AI Text Similarity**
Uses sentence-transformers (all-MiniLM-L6-v2) to convert product names into mathematical embeddings and measure semantic similarity. Catches listings that describe recalled products in different words.

**Layer 2 — Brand Name Detection**
Checks if the brand or manufacturer name from the recall record appears in the listing title. Adds 20 confidence points if found.

**Layer 3 — Word Overlap**
Counts meaningful shared words between the recalled product name and listing title. Adds up to 20 confidence points.

**Layer 4 — CLIP Image Matching**
Downloads listing photos and compares them against recalled product descriptions using OpenAI's CLIP model. Adds bonus confidence points when images visually match the recalled product.

### Confidence Scoring
| Score | Verdict | Action |
|-------|---------|--------|
| 70–100% | HIGH | Flag for removal request |
| 50–69% | REVIEW | Human verification needed |
| 0–49% | LOW | Likely not a recalled product |

### Seller Flagging
Tracks seller usernames across all flagged listings. Sellers with 
multiple recalled product listings are classified by risk level:
- HIGH RISK — 2+ HIGH confidence recalled listings
- MEDIUM RISK — 1 HIGH confidence or 3+ flagged listings
- LOW RISK — single flagged listing

---

## Dashboard Features
- Live filterable table of 26,365 flagged listings
- Filter by verdict, confidence score, product category, and platform
- Color coded by verdict (red/yellow/green)
- Listing detail panel with full match breakdown and direct eBay link
- Reviewer actions: Confirm Match, False Positive, View on eBay
- Analytics charts: verdict breakdown and confidence distribution
- Seller flagging tab with risk level classification
- CSV export for listings and sellers

---

## Platforms Covered
| Platform | Method | Status |
|----------|--------|--------|
| eBay | Official Browse API | Active |
| Craigslist | BeautifulSoup scraper (10 US cities) | Active |
| OfferUp | Selenium scraper | Ready to add |
| Facebook Marketplace | Selenium scraper | Ready to add |

---
## Project Structure
```
cpsc-recall-finder/
├── scraper/
│   ├── cpsc_scraper.py          # loads and cleans CPSC recall database
│   ├── ebay_scraper.py          # searches eBay via Browse API
│   └── craigslist_scraper.py    # scrapes Craigslist across 10 US cities
├── matcher/
│   ├── matcher.py               # AI matching engine and confidence scoring
│   ├── image_matcher.py         # CLIP image-text matching
│   └── seller_analysis.py       # seller flagging and risk classification
├── dashboard/
│   └── app.py                   # Streamlit dashboard
├── data/
│   ├── cpsc_recalls.db          # SQLite database
│   └── *.csv                    # raw CPSC export files
├── docs/
│   └── esafe_integration.md     # eSAFE integration architecture
└── requirements.txt
```

## How To Run

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/CPSC---Finding-Recalled-Banned-Products-for-Sale-Online.git
cd CPSC---Finding-Recalled-Banned-Products-for-Sale-Online
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
pip install git+https://github.com/openai/CLIP.git
```

### 3. Set up environment variables
Create a `.env` file in the root folder:

EBAY_APP_ID= your_ebay_app_id
EBAY_CERT_ID= your_ebay_cert_id

### 4. Download CPSC recall data
- Go to cpsc.gov/Recalls
- Click Export CSV → Download All Recalls
- Click Export CSV → Download All Product Safety Warnings
- Place both CSV files in the data/ folder

### 5. Run the full pipeline
```bash
python scraper/cpsc_scraper.py
python scraper/ebay_scraper.py
python scraper/craigslist_scraper.py
python matcher/matcher.py
python matcher/image_matcher.py
python matcher/seller_analysis.py
streamlit run dashboard/app.py
```

---

## Tech Stack
| Tool | Purpose |
|------|---------|
| Python | Core language |
| sentence-transformers | AI text similarity (all-MiniLM-L6-v2) |
| CLIP (OpenAI) | Image-text matching |
| eBay Browse API | Live eBay listing search |
| BeautifulSoup | Craigslist scraping |
| pandas | Data cleaning and processing |
| SQLite | Local database storage |
| Streamlit | Interactive dashboard |
| Plotly | Analytics charts |
| scikit-learn | Cosine similarity calculations |

---

## eSAFE Integration

---

## Team Muse Crew
Challenge X Submission
U.S. Consumer Product Safety Commission Partnership
