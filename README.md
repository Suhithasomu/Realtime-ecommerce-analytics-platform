# 🛍️ Real-Time E-Commerce Analytics Platform

A full-stack data engineering and machine learning project that processes live e-commerce orders through real-time streaming, fraud detection, sentiment analysis, product recommendations, and inventory monitoring — all displayed on a live analytics dashboard.

> Built as part of an Advanced Systems course | August 2026

---

## 📸 Preview

| Dashboard | Store | Orders |
|-----------|-------|--------|
| 6-page live Streamlit analytics | WordPress + WooCommerce | Fraud orders auto On Hold |

---

## 🏗️ Architecture

```
Customer places order on WooCommerce
         ↓  (detected every 3 seconds)
watch_orders.py → checks customer history → publishes to Kafka → saves to PostgreSQL
         ↓
fraud_detector_ml.py → Rule scoring (11 rules) + Random Forest ML
         ↓
APPROVED  → Confirmation email to customer + notification to admin
FRAUD     → Order ON HOLD in WooCommerce + fraud alert to admin + "Under Review" to customer
         ↓
PostgreSQL ← stores all results
         ↓
Streamlit Dashboard → displays everything live (refreshes every 5s)
```

---

## ⚡ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Store | WordPress + WooCommerce | E-commerce storefront |
| Streaming | Apache Kafka | Real-time event streaming |
| Database | PostgreSQL | Analytics data storage |
| ML | Random Forest (scikit-learn) | Fraud detection (96%+ accuracy) |
| NLP | VADER + TextBlob | Sentiment analysis |
| Recommendations | TF-IDF + Cosine Similarity | Product recommendations |
| Dashboard | Streamlit | 6-page live analytics |
| Infrastructure | Docker (5 containers) | Container orchestration |
| Alerts | Gmail SMTP | 7 automated email types |
| Data Source | RapidAPI (Amazon) | Real product & review data |

---

## 🚀 Features

### 🚨 Real-Time Fraud Detection
- **Hybrid approach**: 11 rule-based scoring rules + trained Random Forest ML model
- Trained on **284,807 real credit card transactions** (Kaggle dataset)
- **96%+ accuracy**, AUC-ROC score of **0.98**
- Fraud orders automatically placed **On Hold** in WooCommerce
- Customer receives **"Order Under Review"** email
- Admin receives **fraud alert** with review link

### 🎭 Sentiment Analysis
- Fetches **real Amazon reviews** via RapidAPI
- Analyzes with **VADER** (social media NLP) + **TextBlob** (linguistic NLP)
- **303 reviews** across **38 products** analyzed
- **90% positive** sentiment across the catalog
- New customer reviews automatically saved to PostgreSQL via review_watcher.py

### 🛍️ Product Recommendations
- **TF-IDF vectorization** converts product descriptions to numerical vectors
- **Cosine similarity** finds similar products
- **200 recommendation pairs** generated for 40 products
- Searchable on dashboard recommendations page

### 📦 Stock Monitoring
- Checks WooCommerce stock every **60 seconds**
- **UPSERT** pattern (no duplicate records)
- Sends **low stock alert** (≤ 5 units) and **out of stock alert** (0 units)
- 1-hour cooldown per product to prevent email spam

### 👥 Customer Management
- Customer registration at `/register` (Profile Builder plugin)
- Login required — guest checkout disabled
- Verified purchase reviews only
- Auto-approved reviews (no moderation needed)
- Cancel button on active orders

### 📊 Live Dashboard (6 Pages)
| Page | What It Shows |
|------|--------------|
| 📊 Overview | Revenue, orders, approved vs blocked, charts |
| 🚨 Fraud Detection | Live fraud gauge, fraud signals, score history |
| 🎭 Sentiment Analysis | Review sentiment charts for all 38 products |
| 🛍️ Recommendations | Product search with TF-IDF similarity scores |
| 📦 Stock Monitor | Live stock levels, low stock alerts |
| 👥 Customers | Segments: New / Returning / Regular / VIP |

### 📧 Automated Emails (7 Types)
| Email | Recipient | Trigger |
|-------|-----------|---------|
| ✅ Order Confirmation | Customer | Approved order |
| ⏳ Order Under Review | Customer | Fraud detected |
| 🛍️ New Order Notification | Admin | Any new order |
| 🚨 Fraud Alert | Admin | Score ≥ 55 |
| 📦 Status Update | Customer | Admin changes status |
| ⚠️ Low Stock Alert | Admin | Stock ≤ 5 units |
| 🚫 Out of Stock Alert | Admin | Stock = 0 |

---

## 🗄️ Database Schema

All analytics data stored in **PostgreSQL** (`ecommerce_db`):

```sql
orders          -- Customer orders with fraud metadata
fraud_scores    -- ML analysis results (rule + ML + final score + status)
product_reviews -- Amazon reviews with VADER/TextBlob sentiment scores
stock_levels    -- Real-time inventory (UPSERT, unique constraint on product_id)
recommendations -- TF-IDF cosine similarity product pairs
products        -- Product catalog (40 real Amazon products)
```

See `db_structure.sql` for the complete schema.

---

## ⚙️ Setup & Installation

### Prerequisites
- Docker Desktop
- Python 3.13
- macOS (scripts use macOS paths — update for Linux/Windows)

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/ecommerce-analytics-platform.git
cd ecommerce-analytics-platform
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create `.env` file with your credentials
```bash
cp .env.example .env
```

Edit `.env` with your values:
```env
GMAIL_SENDER=your_email@gmail.com
GMAIL_PASSWORD=your_gmail_app_password
ADMIN_EMAIL=your_email@gmail.com
RAPIDAPI_KEY=your_rapidapi_key
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ecommerce_db
DB_USER=ecomuser
DB_PASS=ecompass123
```

### 4. Train the fraud model (one time only)
```bash
# Download creditcard.csv from Kaggle first
# https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
python3 train_fraud_model.py
```

### 5. Start everything
```bash
./start_all.sh
```

### 6. Access the system
| Service | URL |
|---------|-----|
| 🛍️ Store | http://localhost:8080/shop |
| 📊 Dashboard | http://localhost:8501 |
| 🔐 WP Admin | http://localhost:8080/wp-admin |

### 7. Stop everything
```bash
./stop_all.sh
```

---

## 🃏 Test Cards (Stripe)

| Card Number | Result |
|-------------|--------|
| `4242 4242 4242 4242` | ✅ Approved |
| `4000 0000 0000 0002` | ❌ Declined |

**Trigger fraud detection:** Use a new email + add expensive item ($1500+) + card `4242 4242 4242 4242`

---

## 📁 Project Structure

```
ecommerce-analytics-platform/
│
├── 🐍 Python Services
│   ├── watch_orders.py          # Order detection + Kafka streaming
│   ├── fraud_detector_ml.py     # ML + rule-based fraud detection
│   ├── stock_monitor.py         # Inventory monitoring (60s)
│   ├── review_watcher.py        # Review sync service (30s)
│   ├── dashboard.py             # 6-page Streamlit dashboard
│   ├── postgres_connector.py    # PostgreSQL connector
│   └── email_alerts.py          # 7 email types via Gmail SMTP
│
├── 🤖 ML & Analytics
│   ├── train_fraud_model.py     # Train Random Forest (run once)
│   ├── recommendation_system.py # TF-IDF recommendations
│   ├── sentiment_all_products.py# Sentiment analysis pipeline
│   ├── fetch_all_reviews.py     # Amazon review fetcher
│   └── create_csv.py            # Amazon product fetcher
│
├── 🗄️ Data
│   ├── products.csv             # 40 real Amazon products
│   ├── fraud_model.pkl          # Trained Random Forest model
│   ├── scaler_amount.pkl        # Amount normalizer
│   ├── scaler_time.pkl          # Time normalizer
│   ├── feature_names.pkl        # ML feature names
│   └── db_structure.sql         # PostgreSQL schema export
│
├── 🐳 Infrastructure
│   ├── docker-compose.yml       # 5 container orchestration
│   ├── apache.conf              # WordPress web server config
│   ├── start_all.sh             # Start all services
│   └── stop_all.sh              # Stop all services
│
├── .env.example                 # Credential template
├── .gitignore                   # Excludes sensitive files
└── README.md                    # This file
```

---

## 🔑 Environment Variables

| Variable | Description |
|----------|-------------|
| `GMAIL_SENDER` | Gmail address for sending emails |
| `GMAIL_PASSWORD` | Gmail app password (not account password) |
| `ADMIN_EMAIL` | Email to receive all admin alerts |
| `RAPIDAPI_KEY` | RapidAPI key for Amazon data |
| `DB_HOST` | PostgreSQL host (localhost) |
| `DB_PORT` | PostgreSQL port (5432) |
| `DB_NAME` | Database name (ecommerce_db) |
| `DB_USER` | Database username |
| `DB_PASS` | Database password |

---

## 📊 System Metrics

| Metric | Value |
|--------|-------|
| Products | 40 real Amazon products |
| Reviews analyzed | 303 (38 products) |
| Positive sentiment | 90% |
| Fraud model accuracy | 96%+ |
| AUC-ROC score | 0.98 |
| Training data | 284,807 transactions |
| Recommendation pairs | 200 |
| Email types | 7 automated |
| Dashboard pages | 6 |
| Docker containers | 5 |
| Background services | 4 |
| Order detection | Every 3 seconds |
| Stock monitoring | Every 60 seconds |

---

## 🧠 ML Fraud Detection Rules

| Rule | Condition | Points |
|------|-----------|--------|
| R1 | High amount ($1000+) + new customer | +40 |
| R2 | Very high amount ($1500+) | +30 |
| R3 | Extremely high amount ($1500+) | +45 |
| R4 | High quantity (>3 items) | +30 |
| R5 | Velocity: 3+ orders/hour | +50 |
| R6 | Card country ≠ shipping country | +35 |
| R7 | Failed payment attempts >2 | +40 |
| R8 | Stripe + high amount + new customer | +35 |
| R9 | Stripe + new customer | +20 |
| R10 | Suspicious round amount | +15 |
| R11 | Bulk purchase (3+ items, $500+) | +40 |

**Threshold: Score ≥ 55 → FRAUD_BLOCKED**


---

## 📄 License

This project is for academic and educational purposes.

---

## 👤 Author

**Suhitha** — Advanced Data Engineering Project, August 2026
