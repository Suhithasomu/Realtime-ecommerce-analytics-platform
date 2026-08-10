"""
PostgreSQL Connector - Replaces Snowflake
Same functions, same behavior, free forever!
"""

import psycopg2
import pandas as pd
from datetime import datetime

# ============================================
# PostgreSQL CREDENTIALS
# ============================================
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ecommerce_db",
    "user": "ecomuser",
    "password": "ecompass123"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def setup_tables():
    """Create all tables (runs once on startup)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(100),
                customer_email VARCHAR(200),
                customer_name VARCHAR(200),
                amount FLOAT,
                quantity INT,
                payment_method VARCHAR(50),
                is_new_customer BOOLEAN,
                card_country VARCHAR(10),
                shipping_country VARCHAR(10),
                products TEXT,
                order_timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Fraud scores table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fraud_scores (
                id SERIAL PRIMARY KEY,
                order_id VARCHAR(100),
                customer_email VARCHAR(200),
                amount FLOAT,
                rule_score INT,
                ml_score INT,
                final_score INT,
                status VARCHAR(50),
                reasons TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(500),
                category VARCHAR(100),
                price FLOAT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Product reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_reviews (
                id SERIAL PRIMARY KEY,
                product_name VARCHAR(500),
                review_text TEXT,
                rating FLOAT,
                textblob_score FLOAT,
                textblob_sentiment VARCHAR(20),
                vader_score FLOAT,
                vader_sentiment VARCHAR(20),
                final_sentiment VARCHAR(20),
                analyzed_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                id SERIAL PRIMARY KEY,
                source_product VARCHAR(500),
                recommended_product VARCHAR(500),
                category VARCHAR(100),
                price VARCHAR(50),
                similarity_score FLOAT,
                rank INT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Stock levels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_levels (
                id SERIAL PRIMARY KEY,
                product_id INT,
                product_name VARCHAR(500),
                stock_level INT,
                status VARCHAR(20),
                checked_at TIMESTAMP DEFAULT NOW()
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
        print("✅ All tables created in PostgreSQL!")
        return True

    except Exception as e:
        print(f"❌ Table creation error: {e}")
        return False


def insert_order(order):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        products = ', '.join(order.get('products', []))[:500]

        cursor.execute("""
            INSERT INTO orders (
                order_id, customer_email, customer_name,
                amount, quantity, payment_method,
                is_new_customer, card_country,
                shipping_country, products, order_timestamp
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            order.get('order_id'),
            order.get('customer_email'),
            order.get('customer_name'),
            float(order.get('amount', 0)),
            int(order.get('quantity', 1)),
            order.get('payment_method'),
            order.get('is_new_customer', False),
            order.get('card_country', 'US'),
            order.get('shipping_country', 'US'),
            products,
            order.get('timestamp')
        ))

        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Order {order.get('order_id')} saved to PostgreSQL!")

    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")


def insert_fraud_score(alert):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        reasons = ', '.join(alert.get('reasons', []))[:1000]

        cursor.execute("""
            INSERT INTO fraud_scores (
                order_id, customer_email, amount,
                rule_score, ml_score, final_score,
                status, reasons
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            alert.get('order_id'),
            alert.get('customer_email'),
            float(alert.get('amount', 0)),
            int(alert.get('rule_score', 0)),
            int(alert.get('ml_score', 0)),
            int(alert.get('final_score', 0)),
            alert.get('status'),
            reasons
        ))

        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Fraud score saved to PostgreSQL!")

    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")


def insert_products():
    try:
        df = pd.read_csv('products.csv')

        conn = get_connection()
        cursor = conn.cursor()

        for _, row in df.iterrows():
            try:
                price_str = str(row.get('Regular price', '0')).replace('$', '').replace(',', '').strip()
                price = float(price_str) if price_str else 0.0

                cursor.execute("""
                    INSERT INTO products (product_name, category, price)
                    VALUES (%s, %s, %s)
                """, (
                    str(row.get('Name', ''))[:500],
                    str(row.get('Categories', ''))[:100],
                    price
                ))
            except Exception as e:
                pass

        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ {len(df)} products saved to PostgreSQL!")

    except Exception as e:
        print(f"❌ Products error: {e}")


def test_connection():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"✅ Connected to PostgreSQL!")
        print(f"   Version: {version[0][:50]}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Make sure PostgreSQL is running: docker-compose up -d postgres")
        return False


if __name__ == "__main__":
    print("🔗 Testing PostgreSQL connection...")
    if test_connection():
        print("\n📊 Creating tables...")
        setup_tables()
        print("\n📦 Importing products...")
        insert_products()
        print("\n✅ PostgreSQL setup complete!")