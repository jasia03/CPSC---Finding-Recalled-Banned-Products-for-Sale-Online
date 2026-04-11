# eSAFE Rapid Tool — Integration Architecture

## Overview
This document describes how the CPSC Recall Finder integrates with 
CPSC's internal eSAFE Rapid Tool to create a seamless workflow for 
identifying, reviewing, and requesting removal of recalled product 
listings on C2C platforms.

---

## Current Workflow (Manual)
1. CPSC staff manually search C2C platforms for recalled products
2. Staff copy listing URLs into eSAFE manually
3. eSAFE generates removal requests to platforms
4. Platforms review and remove listings

## Proposed Workflow (Automated)
1. Recall Finder automatically scrapes eBay every 24 hours
2. AI matcher scores all new listings
3. HIGH confidence matches are automatically pushed to eSAFE
4. REVIEW matches appear in dashboard for human verification
5. Verified matches are pushed to eSAFE with one click
6. eSAFE generates and sends removal requests as normal

---

## Integration Method

### Option A — REST API (Recommended)
The Recall Finder exposes a REST API endpoint that eSAFE can poll 
periodically to retrieve new flagged listings.

**Endpoint:**

GET /api/flagged-listings
**Response format:**
```json
{
  "listings": [
    {
      "recall_number": "26-381",
      "recalled_product": "baby walker",
      "listing_title": "Baby Walker Used Good Condition",
      "platform": "eBay",
      "listing_url": "https://www.ebay.com/itm/...",
      "price": "USD 25.00",
      "location": "US",
      "confidence_score": 100.0,
      "verdict": "HIGH",
      "hazard_description": "Fall hazard to children",
      "matched_at": "2026-04-10T14:23:00Z"
    }
  ],
  "total": 575,
  "high_confidence": 312,
  "needs_review": 198
}
```

### Option B — Webhook (Real-time)
The Recall Finder sends a POST request to eSAFE immediately when a 
HIGH confidence match is found, enabling real-time processing.

**Webhook payload:**
```json
{
  "event": "high_confidence_match",
  "listing": {
    "recall_number": "26-381",
    "recalled_product": "baby walker",
    "listing_url": "https://www.ebay.com/itm/...",
    "confidence_score": 100.0,
    "platform": "eBay"
  }
}
```

---

## Automated Scheduling
The scraper runs on a 24-hour schedule using a cron job:
runs every day at 2am
0 2 * * * python scraper/ebay_scraper.py
0 3 * * * python matcher/matcher.py
This ensures CPSC always has fresh data without any manual effort.

---

## Data Flow Diagram
CPSC Recall DB → eBay Scraper → AI Matcher → SQLite DB
↓
eSAFE Rapid Tool ← REST API / Webhook
↓
Dashboard (Human Review)
↓
Removal Request to Platform
---

## Platform Expansion
The system is designed to add new C2C platforms easily. Each new 
platform only requires a new scraper module:

| Platform | Status | Method |
|----------|--------|--------|
| eBay | Active | Official Browse API |
| Craigslist | Ready to add | BeautifulSoup scraper |
| OfferUp | Ready to add | Selenium scraper |
| Facebook Marketplace | Ready to add | Selenium scraper |

---

## Human Oversight
In line with CPSC requirements, the system maintains human oversight 
at every step:

- LOW confidence matches are never sent to eSAFE automatically
- REVIEW matches require manual approval in the dashboard
- Only HIGH confidence matches can be auto-forwarded
- All reviewer actions are logged with timestamp and user ID
- CPSC staff can override any automated decision

---

## Security
- All API communications use HTTPS
- eSAFE API key stored in environment variables, never in code
- No eBay user data is stored — only public listing information
- Database access restricted to CPSC internal network