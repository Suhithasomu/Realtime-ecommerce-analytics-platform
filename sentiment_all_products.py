import requests
import json
import time
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
from postgres_connector import get_connection

RAPIDAPI_KEY = "YOUR_RAPIDAPI_KEY"

print("🎭 Analyzing ALL products sentiment...")
print("="*50)

vader = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    blob = TextBlob(text)
    textblob_score = blob.sentiment.polarity
    vader_scores = vader.polarity_scores(text)
    vader_compound = vader_scores['compound']

    if textblob_score > 0.1:
        textblob_sentiment = "POSITIVE"
    elif textblob_score < -0.1:
        textblob_sentiment = "NEGATIVE"
    else:
        textblob_sentiment = "NEUTRAL"

    if vader_compound >= 0.05:
        vader_sentiment = "POSITIVE"
    elif vader_compound <= -0.05:
        vader_sentiment = "NEGATIVE"
    else:
        vader_sentiment = "NEUTRAL"

    if textblob_sentiment == vader_sentiment:
        final = textblob_sentiment
    elif textblob_sentiment == "NEUTRAL":
        final = vader_sentiment
    else:
        final = vader_sentiment

    return {
        "textblob_score": round(textblob_score, 4),
        "textblob_sentiment": textblob_sentiment,
        "vader_score": round(vader_compound, 4),
        "vader_sentiment": vader_sentiment,
        "final_sentiment": final
    }

def get_reviews_by_asin(asin, max_reviews=5):
    url = "https://real-time-amazon-data.p.rapidapi.com/product-reviews"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
    }
    params = {
        "asin": asin,
        "country": "US",
        "sort_by": "TOP_REVIEWS",
        "star_rating": "ALL",
        "verified_purchases_only": "false",
        "page": "1"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        reviews = []
        for r in data.get("data", {}).get("reviews", [])[:max_reviews]:
            text = r.get("review_comment", "")
            rating = r.get("review_star_rating", 0)
            if text:
                reviews.append({
                    "text": text,
                    "rating": float(rating) if rating else 0.0
                })
        return reviews
    except:
        return []

def search_product_asin(product_name):
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
    }
    params = {
        "query": product_name[:50],
        "page": "1",
        "country": "US"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        products = data.get("data", {}).get("products", [])
        if products:
            return products[0].get("asin", "")
    except:
        pass
    return ""

def save_reviews_to_postgres(product_name, reviews, sentiments):
    """Save reviews to PostgreSQL instead of Snowflake"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for review, sentiment in zip(reviews, sentiments):
            cursor.execute("""
                INSERT INTO product_reviews (
                    product_name, review_text, rating,
                    textblob_score, textblob_sentiment,
                    vader_score, vader_sentiment,
                    final_sentiment
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
        print(f"❌ Save error: {str(e)}")

# Load all products from CSV
df = pd.read_csv('products.csv')
products = df['Name'].dropna().tolist()
print(f"Found {len(products)} products to analyze!")
print("This will take a few minutes...")
print("-"*50)

total_reviews = 0
analyzed_products = 0
skipped = 0

for i, product_name in enumerate(products):
    try:
        print(f"\n[{i+1}/{len(products)}] {product_name[:50]}...")

        # Search for ASIN
        asin = search_product_asin(product_name)
        if not asin:
            print(f"   ⚠️ No ASIN found - skipping")
            skipped += 1
            continue

        # Get reviews
        reviews = get_reviews_by_asin(asin, max_reviews=5)
        if not reviews:
            print(f"   ⚠️ No reviews found - skipping")
            skipped += 1
            continue

        # Analyze sentiment
        sentiments = [analyze_sentiment(r['text']) for r in reviews]

        # Save to PostgreSQL
        save_reviews_to_postgres(product_name, reviews, sentiments)

        positive = sum(1 for s in sentiments if s['final_sentiment'] == 'POSITIVE')
        negative = sum(1 for s in sentiments if s['final_sentiment'] == 'NEGATIVE')
        neutral = sum(1 for s in sentiments if s['final_sentiment'] == 'NEUTRAL')

        print(f"   ✅ {positive} positive | ❌ {negative} negative | 😐 {neutral} neutral")

        total_reviews += len(reviews)
        analyzed_products += 1

        # Wait to avoid API rate limit
        time.sleep(1)

    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        continue

print("\n" + "="*50)
print(f"🎉 Sentiment Analysis Complete!")
print(f"   Products analyzed: {analyzed_products}/{len(products)}")
print(f"   Skipped: {skipped}")
print(f"   Total reviews: {total_reviews}")
print(f"   All saved to PostgreSQL! ✅")
print("="*50)

# Verify saved data
try:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT product_name) FROM product_reviews")
    product_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM product_reviews")
    review_count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    print(f"\n📊 Database Summary:")
    print(f"   Products with reviews: {product_count}")
    print(f"   Total reviews stored: {review_count}")
except Exception as e:
    print(f"❌ Verify error: {e}")