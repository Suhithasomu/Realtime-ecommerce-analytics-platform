import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from postgres_connector import get_connection
import json

print("🛍️ Building Recommendation System...")
print("="*50)

# ============================================
# Step 1 — Load products from CSV
# ============================================
df = pd.read_csv('products.csv')
df = df.dropna(subset=['Name'])
df['id'] = range(len(df))

print(f"✅ Loaded {len(df)} products!")

# ============================================
# Step 2 — Build content based recommendations
# ============================================
print("\n🔧 Building recommendation engine...")

# Combine name and category for better matching
df['content'] = df['Name'].fillna('') + ' ' + df['Categories'].fillna('')

# Build TF-IDF matrix
tfidf = TfidfVectorizer(stop_words='english', max_features=100)
tfidf_matrix = tfidf.fit_transform(df['content'])

# Calculate cosine similarity between all products
cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)
print(f"✅ Similarity matrix built: {cosine_sim.shape}")

# ============================================
# Step 3 — Recommendation function
# ============================================
def get_recommendations(product_name, n=5):
    try:
        # Find closest matching product
        matches = df[df['Name'].str.contains(
            product_name[:20], case=False, na=False
        )]
        
        if matches.empty:
            return []
        
        idx = matches.index[0]
        
        # Get similarity scores
        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)
        sim_scores = sim_scores[1:n+1]
        
        product_indices = [i[0] for i in sim_scores]
        recommendations = []
        
        for i, prod_idx in enumerate(product_indices):
            recommendations.append({
                "rank": i + 1,
                "product": df.iloc[prod_idx]['Name'][:80],
                "category": df.iloc[prod_idx]['Categories'],
                "price": df.iloc[prod_idx]['Regular price'],
                "similarity": round(sim_scores[i][1] * 100, 1)
            })
        
        return recommendations
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

# ============================================
# Step 4 — Save recommendations to Snowflake
# ============================================
def create_recommendations_table():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS 
            recommendations (
                source_product VARCHAR(500),
                recommended_product VARCHAR(500),
                category VARCHAR(100),
                price VARCHAR(50),
                similarity_score FLOAT,
                rank INT,
                CREATED_AT TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Recommendations table created!")
    except Exception as e:
        print(f"❌ Table error: {str(e)}")

def save_recommendations(product_name, recommendations):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        for rec in recommendations:
            cursor.execute("""
                INSERT INTO recommendations (
                    source_product, recommended_product,
                    category, price,
                    similarity_score, rank
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                product_name[:500],
                rec['product'][:500],
                str(rec['category'])[:100],
                str(rec['price'])[:50],
                float(rec["similarity"]),
                rec['rank']
            ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Save error: {str(e)}")

# ============================================
# Step 5 — Generate recommendations for all
# ============================================
create_recommendations_table()

print("\n🔮 Generating recommendations for all products...")

total_saved = 0
for _, row in df.iterrows():
    product_name = row['Name']
    recs = get_recommendations(product_name, n=5)
    if recs:
        save_recommendations(product_name, recs)
        total_saved += 1

print(f"✅ Generated recommendations for {total_saved} products!")

# ============================================
# Step 6 — Test it!
# ============================================
print("\n🧪 Testing recommendations...")
test_products = [
    "laptop",
    "headphones",
    "gaming",
    "smartphone"
]

for test in test_products:
    recs = get_recommendations(test, n=3)
    if recs:
        print(f"\n🛍️ Because you searched '{test}':")
        for rec in recs:
            print(f"   {rec['rank']}. {rec['product'][:50]}")
            print(f"      Category: {rec['category']} | Score: {rec['similarity']}%")

print("\n" + "="*50)
print("🎉 Recommendation System Complete!")
print(f"   Algorithm: Content-based filtering (TF-IDF + Cosine Similarity)")
print(f"   Products: {len(df)}")
print(f"   Saved to Snowflake: ✅")
print("="*50)
