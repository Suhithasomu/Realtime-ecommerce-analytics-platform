"""
Fetch Reviews - Optimized for 100 API calls
Strategy: 1 ASIN search + 1 review fetch per product = 2 calls per product
40 products x 2 calls = 80 calls total (within 100 limit!)
"""
import requests
import time
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
from postgres_connector import get_connection

RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY"  # ← Update this!

print("🎭 Fetching Reviews - Optimized for 100 API Calls")
print("="*50)

vader = SentimentIntensityAnalyzer()
api_calls_used = 0

def analyze_sentiment(text):
    blob = TextBlob(text)
    textblob_score = blob.sentiment.polarity
    vader_scores = vader.polarity_scores(text)
    vader_compound = vader_scores['compound']
    textblob_sentiment = "POSITIVE" if textblob_score > 0.1 else "NEGATIVE" if textblob_score < -0.1 else "NEUTRAL"
    vader_sentiment = "POSITIVE" if vader_compound >= 0.05 else "NEGATIVE" if vader_compound <= -0.05 else "NEUTRAL"
    final = textblob_sentiment if textblob_sentiment == vader_sentiment else vader_sentiment
    return {
        "textblob_score": round(textblob_score, 4),
        "textblob_sentiment": textblob_sentiment,
        "vader_score": round(vader_compound, 4),
        "vader_sentiment": vader_sentiment,
        "final_sentiment": final
    }

def search_product_asin(product_name):
    global api_calls_used
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params={
            "query": product_name[:50],
            "page": "1",
            "country": "US"
        })
        api_calls_used += 1
        print(f"   API calls used: {api_calls_used}/100")

        if response.status_code == 429:
            print("   ❌ Quota exceeded!")
            return None

        products = response.json().get("data", {}).get("products", [])
        if products:
            return products[0].get("asin", "")
    except Exception as e:
        print(f"   Search error: {e}")
    return ""

def fetch_reviews(asin):
    global api_calls_used
    url = "https://real-time-amazon-data.p.rapidapi.com/product-reviews"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params={
            "asin": asin,
            "country": "US",
            "sort_by": "TOP_REVIEWS",
            "star_rating": "ALL",
            "verified_purchases_only": "false",
            "page": "1"
        })
        api_calls_used += 1
        print(f"   API calls used: {api_calls_used}/100")

        if response.status_code == 429:
            print("   ❌ Quota exceeded!")
            return []

        reviews = []
        for r in response.json().get("data", {}).get("reviews", []):
            text = r.get("review_comment", "")
            rating = r.get("review_star_rating", 0)
            if text:
                reviews.append({
                    "text": text,
                    "rating": float(rating) if rating else 0.0
                })
        return reviews
    except Exception as e:
        print(f"   Review error: {e}")
    return []

def clear_and_save(product_name, reviews, sentiments):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM product_reviews WHERE product_name = %s", (product_name[:500],))
        for review, sentiment in zip(reviews, sentiments):
            cursor.execute("""
                INSERT INTO product_reviews (
                    product_name, review_text, rating,
                    textblob_score, textblob_sentiment,
                    vader_score, vader_sentiment, final_sentiment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                product_name[:500],
                review['text'][:5000],
                review['rating'],
                sentiment['textblob_score'],
                sentiment['textblob_sentiment'],
                sentiment['vader_score'],
                sentiment['vader_sentiment'],
                sentiment['final_sentiment']
            ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"   Save error: {e}")

# ============================================================
# MAIN
# ============================================================
df = pd.read_csv('/Users/suhitha/ecommerce-project/products.csv')
products = df['Name'].dropna().tolist()

print(f"Found {len(products)} products")
print(f"API Budget: 100 calls")
print(f"Strategy: 2 calls per product (1 search + 1 reviews)")
print(f"Max products: 50 (using 80 calls, saving 20 as buffer)")
print("-"*50)

total_reviews = 0
analyzed_products = 0

for i, product_name in enumerate(products):
    # Stop if running low on API calls
    if api_calls_used >= 90:
        print(f"\n⚠️  Stopping - 90 API calls used. Saving 10 as buffer.")
        break

    try:
        print(f"\n[{i+1}/{len(products)}] {product_name[:50]}...")

        # Step 1: Find ASIN (1 API call)
        asin = search_product_asin(product_name)
        if not asin:
            print("   ⚠️  No ASIN found - skipping")
            continue

        if asin is None:  # Quota exceeded
            break

        print(f"   ASIN: {asin}")

        # Step 2: Fetch reviews (1 API call)
        if api_calls_used >= 90:
            break

        reviews = fetch_reviews(asin)
        if not reviews:
            print("   ⚠️  No reviews found")
            continue

        # Analyze sentiment
        sentiments = [analyze_sentiment(r['text']) for r in reviews]

        # Save to PostgreSQL
        clear_and_save(product_name, reviews, sentiments)

        positive = sum(1 for s in sentiments if s['final_sentiment'] == 'POSITIVE')
        negative = sum(1 for s in sentiments if s['final_sentiment'] == 'NEGATIVE')
        neutral = sum(1 for s in sentiments if s['final_sentiment'] == 'NEUTRAL')

        print(f"   ✅ Saved {len(reviews)} reviews")
        print(f"   😊 {positive} positive | 😞 {negative} negative | 😐 {neutral} neutral")

        total_reviews += len(reviews)
        analyzed_products += 1

        # Small delay to avoid rate limiting
        time.sleep(1.5)

    except Exception as e:
        print(f"   ❌ Error: {e}")
        continue

# ============================================================
# FINAL SUMMARY
# ============================================================
print("\n" + "="*50)
print(f"🎉 COMPLETE!")
print(f"   Products analyzed: {analyzed_products}/{len(products)}")
print(f"   Total reviews: {total_reviews}")
print(f"   API calls used: {api_calls_used}/100")
print(f"   API calls remaining: {100 - api_calls_used}")
print("="*50)

# Database summary
conn = get_connection()
cursor = conn.cursor()
cursor.execute("""
    SELECT 
        COUNT(DISTINCT product_name) as products,
        COUNT(*) as total,
        SUM(CASE WHEN final_sentiment='POSITIVE' THEN 1 ELSE 0 END) as pos,
        SUM(CASE WHEN final_sentiment='NEGATIVE' THEN 1 ELSE 0 END) as neg,
        SUM(CASE WHEN final_sentiment='NEUTRAL' THEN 1 ELSE 0 END) as neu
    FROM product_reviews
""")
row = cursor.fetchone()
cursor.close()
conn.close()

print(f"\n📊 Final Database Summary:")
print(f"   Products with reviews: {row[0]}")
print(f"   Total reviews: {row[1]}")
print(f"   😊 Positive: {row[2]}")
print(f"   😞 Negative: {row[3]}")
print(f"   😐 Neutral: {row[4]}")