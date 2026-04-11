# CPSC---Finding-Recalled-Banned-Products-for-Sale-Online

## Live Demo
🔗 [View the live dashboard here](https://cpsc---finding-recalled-banned-appucts-for-sale-online-amzepch.streamlit.app/)

# CPSC Recall Finder
### George Mason University — Challenge X

An automated system that identifies recalled and banned consumer products 
listed for sale on consumer-to-consumer (C2C) online platforms like eBay, 
using AI-powered matching and a live review dashboard.

---

## The Problem
The U.S. Consumer Product Safety Commission (CPSC) currently monitors C2C 
platforms manually to find recalled products still being sold. This is 
slow, inefficient, and means dangerous products stay listed longer than 
they should.

## Our Solution
An end-to-end automated pipeline that:
1. Loads all CPSC recalled and banned products into a database
2. Searches eBay for listings matching those products
3. Uses AI to score each listing's likelihood of being a recalled product
4. Presents flagged listings in a dashboard for human review and action

---

## Results
- **9,318** recalled products loaded from CPSC database
- **575** real eBay listings found matching recalled products
- **Baby walkers** (federally banned) found selling for $15–$40
- **Infant walkers, bed rails, baby bath seats, dressers** all flagged
- Confidence scoring system with **100% accuracy** on exact matches

---

## How It Works

### Matching Engine — 3 Layers
**Layer 1 — AI Text Similarity**
Uses `sentence-transformers` (all-MiniLM-L6-v2) to convert product names 
into mathematical embeddings and measure semantic similarity. Catches 
listings that describe recalled products in different words.

**Layer 2 — Brand Name Detection**
Checks if the brand or manufacturer name from the recall record appears 
in the listing title. Adds 20 confidence points if found.

**Layer 3 — Word Overlap**
Counts meaningful shared words between the recalled product name and 
listing title. Adds up to 20 confidence points.

### Confidence Scoring
| Score | Verdict | Action |
|-------|---------|--------|
| 70–100% | HIGH | Flag for removal request |
| 50–69% | REVIEW | Human verification needed |
| 0–49% | LOW | Likely not a recalled product |

---

## Dashboard Features
- Live filterable table of all flagged listings
- Color coded by verdict (red/yellow/green)
- Listing detail panel with full match breakdown
- Reviewer actions: Confirm Match, False Positive, View on eBay
- Analytics charts: verdict breakdown and confidence distribution
- CSV export for removal request processing

---

## Project Structure

cpsc-recall-finder/
├── scraper/
│   ├── cpsc_scraper.py      # loads and cleans CPSC recall database
│   └── ebay_scraper.py      # searches eBay via Browse API
├── matcher/
│   └── matcher.py           # AI matching engine and confidence scoring
├── dashboard/
│   └── app.py               # Streamlit dashboard
├── data/
│   ├── cpsc_recalls.db      # SQLite database
│   └── *.csv                # raw CPSC export files
└── requirements.txt

---

## How To Run

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/CPSC---Finding-Recalled-Banned-Products-for-Sale-Online.git
cd CPSC---Finding-Recalled-Banned-Products-for-Sale-Online
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
Create a `.env` file in the root folder:

EBAY_APP_ID=x
EBAY_CERT_ID=y

### 4. Download CPSC recall data
- Go to cpsc.gov/Recalls
- Click Export CSV → Download All Recalls
- Click Export CSV → Download All Product Safety Warnings
- Place both CSV files in the `data/` folder

### 5. Run the pipeline
```bash
# Build the recall database
python scraper/cpsc_scraper.py

# Search eBay for recalled products
python scraper/ebay_scraper.py

# Run the AI matcher
python matcher/matcher.py

# Launch the dashboard
streamlit run dashboard/app.py
```

---

## Tech Stack
| Tool | Purpose |
|------|---------|
| Python | Core language |
| sentence-transformers | AI text similarity (all-MiniLM-L6-v2) |
| eBay Browse API | Live C2C listing search |
| pandas | Data cleaning and processing |
| SQLite | Local database storage |
| Streamlit | Interactive dashboard |
| Plotly | Analytics charts |
| scikit-learn | Cosine similarity calculations |

---

## eSAFE Integration
This system is designed to integrate with CPSC's eSAFE Rapid Tool. 
Each flagged listing is stored with a structured JSON schema that can 
be consumed by eSAFE via a REST API or webhook. See 
`docs/esafe_integration.md` for the full integration architecture.

---

## Team
George Mason University — Challenge X Submission  
U.S. Consumer Product Safety Commission Partnership