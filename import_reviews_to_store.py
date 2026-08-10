"""
Import Reviews from PostgreSQL to WooCommerce Store - FIXED VERSION
"""
import subprocess
import json
from postgres_connector import get_connection
import time
import random

print("📝 Importing Reviews from PostgreSQL to WooCommerce Store")
print("="*60)

DOCKER_COMPOSE = '/Users/suhitha/ecommerce-project/docker-compose.yml'

def run_wp_command(php_code):
    """Run WP-CLI command in WordPress container"""
    result = subprocess.run(
        ['docker', 'compose', '-f', DOCKER_COMPOSE,
         'exec', '-T', 'wordpress',
         'php', 'wp-cli.phar', 'eval', php_code, '--allow-root'],
        capture_output=True, text=True
    )
    return result.stdout.strip(), result.stderr.strip()

def get_reviews_from_postgres():
    """Get all reviews from PostgreSQL"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product_name, review_text, rating, final_sentiment
        FROM product_reviews
        ORDER BY product_name, rating DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def find_woo_product(product_name):
    """Find WooCommerce product ID"""
    clean = product_name[:35].replace("'", "").replace('"', '').replace('\\', '').replace('&', 'and').replace(';', '')
    php = f"""
$args = array('limit' => 5, 's' => '{clean}', 'status' => 'publish');
$products = wc_get_products($args);
if(!empty($products)) {{
    echo $products[0]->get_id();
}} else {{
    echo '0';
}}
"""
    out, err = run_wp_command(php)
    try:
        return int(out.strip())
    except:
        return 0

def clear_reviews(product_id):
    """Clear existing reviews"""
    php = f"""
$comments = get_comments(array(
    'post_id' => {product_id},
    'type' => 'review'
));
foreach($comments as $c) {{
    wp_delete_comment($c->comment_ID, true);
}}
echo count($comments);
"""
    out, _ = run_wp_command(php)
    return out.strip()

def add_single_review(product_id, review_text, rating, sentiment):
    """Add one review at a time using wp comment create"""

    # Clean text
    clean_text = review_text[:200]
    clean_text = clean_text.replace("'", "").replace('"', '').replace('\\', '').replace('\n', ' ').replace('\r', '')
    clean_text = clean_text.replace('`', '').replace('$', '').replace(';', '').replace('&', 'and')

    rating_int = max(1, min(5, int(float(rating) if rating else 3)))

    # Random reviewer name
    if sentiment == 'POSITIVE':
        names = ['John Smith', 'Sarah Johnson', 'Mike Davis', 'Emily Wilson', 'David Brown', 'Lisa Anderson']
    elif sentiment == 'NEGATIVE':
        names = ['Unhappy Buyer', 'Disappointed Customer', 'Frustrated User']
    else:
        names = ['Verified Buyer', 'Regular Customer', 'Product User']

    name = random.choice(names)
    rand_num = random.randint(1000, 9999)
    email = f"customer{rand_num}@verified.com"

    php = f"""
$pid = {product_id};
$data = array(
    'comment_post_ID' => $pid,
    'comment_author' => '{name}',
    'comment_author_email' => '{email}',
    'comment_content' => '{clean_text}',
    'comment_type' => 'review',
    'comment_status' => 'approve',
    'comment_approved' => 1
);
$cid = wp_insert_comment($data);
if($cid && !is_wp_error($cid)) {{
    update_comment_meta($cid, 'rating', {rating_int});
    update_comment_meta($cid, 'verified', 1);
    WC_Comments::clear_transients($pid);
    echo 'ok:' . $cid;
}} else {{
    echo 'fail';
}}
"""
    out, err = run_wp_command(php)
    return 'ok' in out

# ============================================================
# MAIN
# ============================================================

# Enable reviews
run_wp_command("""
update_option('woocommerce_enable_reviews', 'yes');
update_option('woocommerce_enable_review_rating', 'yes');
update_option('woocommerce_review_rating_required', 'no');
echo 'ok';
""")
print("✅ Reviews enabled in WooCommerce")

# Get reviews
reviews = get_reviews_from_postgres()
print(f"✅ Found {len(reviews)} reviews in PostgreSQL\n")

# Group by product
product_reviews = {}
for row in reviews:
    name, text, rating, sentiment = row
    if name not in product_reviews:
        product_reviews[name] = []
    product_reviews[name].append({
        'text': text,
        'rating': rating,
        'sentiment': sentiment
    })

print(f"Products to process: {len(product_reviews)}")
print("-"*60)

imported = 0
skipped = 0
total_added = 0
count = 0

for product_name, review_list in product_reviews.items():
    count += 1
    print(f"\n[{count}/{len(product_reviews)}] {product_name[:55]}...")

    # Find product in WooCommerce
    product_id = find_woo_product(product_name)

    if product_id == 0:
        print(f"   ⚠️  Not found in store - skipping")
        skipped += 1
        continue

    print(f"   📦 Product ID: {product_id}")

    # Clear old reviews
    cleared = clear_reviews(product_id)
    if cleared and cleared != '0':
        print(f"   🗑️  Cleared {cleared} old reviews")

    # Add each review one by one
    added = 0
    for review in review_list:
        success = add_single_review(
            product_id,
            review['text'],
            review['rating'],
            review['sentiment']
        )
        if success:
            added += 1
            total_added += 1
        time.sleep(0.3)

    print(f"   ✅ Added {added}/{len(review_list)} reviews")
    imported += 1

# Final summary
print("\n" + "="*60)
print("🎉 IMPORT COMPLETE!")
print(f"   Products with reviews: {imported}")
print(f"   Products not found:    {skipped}")
print(f"   Total reviews added:   {total_added}")
print()
print("✅ Go check your store!")
print("   http://localhost:8080/shop")
print("   Click any product → scroll down → see reviews!")
print("="*60)