import sys
sys.path.insert(0, '/Users/suhitha/ecommerce-project')

import subprocess
import time
from postgres_connector import get_connection
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

DOCKER_COMPOSE = '/Users/suhitha/ecommerce-project/docker-compose.yml'
analyzer = SentimentIntensityAnalyzer()

print("👀 Review Watcher Running...")
print("Watching for new customer reviews every 30 seconds")
print("="*50)


def setup_db():
    """Add wp_comment_id column if not exists"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name='product_reviews' AND column_name='wp_comment_id'
        """)
        if not cursor.fetchone():
            cursor.execute('ALTER TABLE product_reviews ADD COLUMN wp_comment_id INTEGER')
            conn.commit()
            print("✅ Added wp_comment_id column")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"DB setup error: {e}")


def get_wordpress_reviews():
    """Get all product reviews from WordPress database"""
    php_code = """
global $wpdb;
$sql = "SELECT c.comment_ID, c.comment_content, c.comment_post_ID
        FROM {$wpdb->comments} c
        JOIN {$wpdb->posts} p ON c.comment_post_ID = p.ID
        WHERE p.post_type = 'product'
        AND c.comment_type = 'review'
        AND c.comment_approved = '1'
        ORDER BY c.comment_ID DESC
        LIMIT 50";
$comments = $wpdb->get_results($sql);
foreach($comments as $c) {
    $rating = get_comment_meta($c->comment_ID, 'rating', true);
    $product = wc_get_product($c->comment_post_ID);
    if($product) {
        $name = str_replace('|||', '', $product->get_name());
        $text = str_replace('|||', '', $c->comment_content);
        echo $c->comment_ID . '|||' . $name . '|||' . $text . '|||' . ($rating ? $rating : 5) . "\n";
    }
}
"""
    result = subprocess.run(
        ['docker', 'compose', '-f', DOCKER_COMPOSE,
         'exec', '-T', 'wordpress',
         'php', 'wp-cli.phar', 'eval',
         php_code, '--allow-root'],
        capture_output=True, text=True
    )

    reviews = []
    if result.stdout:
        for line in result.stdout.strip().split('\n'):
            if '|||' in line:
                parts = line.split('|||', 3)
                if len(parts) == 4:
                    try:
                        reviews.append({
                            'comment_id': int(parts[0].strip()),
                            'product_name': parts[1].strip(),
                            'review_text': parts[2].strip(),
                            'rating': int(float(parts[3].strip()))
                        })
                    except:
                        pass
    return reviews


def analyze_sentiment(text):
    """Analyze review sentiment using VADER + TextBlob"""
    blob = TextBlob(text)
    tb_score = blob.sentiment.polarity
    vader_scores = analyzer.polarity_scores(text)
    vader_compound = vader_scores['compound']

    tb_sent = "POSITIVE" if tb_score > 0.1 else "NEGATIVE" if tb_score < -0.1 else "NEUTRAL"
    vader_sent = "POSITIVE" if vader_compound >= 0.05 else "NEGATIVE" if vader_compound <= -0.05 else "NEUTRAL"
    final = tb_sent if tb_sent == vader_sent else vader_sent

    return round(tb_score, 4), tb_sent, round(vader_compound, 4), vader_sent, final


def get_saved_comment_ids():
    """Get WordPress comment IDs already in PostgreSQL"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT wp_comment_id FROM product_reviews WHERE wp_comment_id IS NOT NULL')
        ids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return ids
    except:
        return []


def save_review(review):
    """Save review to PostgreSQL with NLP sentiment analysis"""
    try:
        tb_score, tb_sent, vader_score, vader_sent, final_sent = analyze_sentiment(review['review_text'])

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO product_reviews (
                product_name, review_text, rating,
                textblob_score, textblob_sentiment,
                vader_score, vader_sentiment,
                final_sentiment, wp_comment_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            review['product_name'][:500],
            review['review_text'][:5000],
            review['rating'],
            tb_score, tb_sent,
            vader_score, vader_sent,
            final_sent,
            review['comment_id']
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return True, final_sent
    except Exception as e:
        print(f"   ❌ Save error: {e}")
        return False, None


# Setup database
setup_db()

# Main monitoring loop
check_count = 0
while True:
    try:
        check_count += 1
        saved_ids = get_saved_comment_ids()
        reviews = get_wordpress_reviews()
        new_reviews = [r for r in reviews if r['comment_id'] not in saved_ids]

        if new_reviews:
            print(f"\n🆕 Found {len(new_reviews)} new review(s)!")
            for review in new_reviews:
                print(f"   📦 Product: {review['product_name'][:50]}")
                print(f"   💬 Review:  {review['review_text'][:60]}")
                print(f"   ⭐ Rating:  {review['rating']} stars")

                success, sentiment = save_review(review)
                if success:
                    emoji = "😊" if sentiment == "POSITIVE" else "😞" if sentiment == "NEGATIVE" else "😐"
                    print(f"   ✅ Saved! Sentiment: {emoji} {sentiment}")
                else:
                    print(f"   ❌ Failed to save!")
            print()
        else:
            print(f"[{time.strftime('%H:%M:%S')}] Check #{check_count} - No new reviews. Waiting 30 seconds...")

    except Exception as e:
        print(f"❌ Error: {e}")

    time.sleep(30)