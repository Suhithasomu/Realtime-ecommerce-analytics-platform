import subprocess
import time
from email_alerts import send_low_stock_alert, send_out_of_stock_alert
from postgres_connector import get_connection
from datetime import datetime

print("📦 Real-Time Stock Monitor Starting...")
print("="*50)

# ============================================================
# CONFIGURATION
# ============================================================
LOW_STOCK_THRESHOLD = 5
CHECK_INTERVAL = 60
ALERT_COOLDOWN = 3600

# Track when we last sent alerts (avoid spam)
last_alert_sent = {}


def get_stock_levels():
    """Fetch real stock levels from WooCommerce"""
    try:
        result = subprocess.run(
            ['docker', 'compose', '-f',
             '/Users/suhitha/ecommerce-project/docker-compose.yml',
             'exec', '-T', 'wordpress',
             'php', 'wp-cli.phar', 'eval',
             '''
$products = wc_get_products(array("limit" => -1));
foreach($products as $product) {
    $stock = $product->get_stock_quantity();
    $name = $product->get_name();
    $id = $product->get_id();
    $price = $product->get_price();
    if($stock !== null) {
        echo $id . "|" . $stock . "|" . $name . "|" . $price . "\n";
    }
}
''',
             '--allow-root'],
            capture_output=True, text=True
        )

        products = []
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if '|' in line:
                    parts = line.split('|', 3)
                    if len(parts) >= 3:
                        try:
                            stock_val = parts[1].strip()
                            stock = int(stock_val) if stock_val.lstrip('-').isdigit() else 0
                            products.append({
                                'id': int(parts[0]),
                                'stock': max(0, stock),
                                'name': parts[2].strip(),
                                'price': float(parts[3]) if len(parts) > 3 and parts[3].strip() else 0.0
                            })
                        except:
                            pass
        return products
    except Exception as e:
        print(f"❌ Error fetching stock: {e}")
        return []


def save_stock_to_postgres(products):
    """Save stock levels to PostgreSQL - UPSERT (no duplicates!)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Add unique constraint if not exists
        try:
            cursor.execute('''
                ALTER TABLE stock_levels 
                ADD CONSTRAINT unique_product_id UNIQUE (product_id)
            ''')
            conn.commit()
        except:
            conn.rollback()

        for product in products:
            stock = product['stock']
            if stock == 0:
                status = 'OUT_OF_STOCK'
            elif stock <= LOW_STOCK_THRESHOLD:
                status = 'LOW_STOCK'
            else:
                status = 'IN_STOCK'

            # UPSERT - Update if exists, Insert if new
            cursor.execute("""
                INSERT INTO stock_levels 
                (product_id, product_name, stock_level, status, checked_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (product_id)
                DO UPDATE SET
                    stock_level = EXCLUDED.stock_level,
                    status = EXCLUDED.status,
                    checked_at = NOW()
            """, (
                product['id'],
                product['name'][:500],
                stock,
                status
            ))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ PostgreSQL error: {e}")


def check_and_alert(products):
    """Check stock levels and send email alerts"""
    out_of_stock = []
    low_stock = []
    in_stock = []
    current_time = time.time()

    for product in products:
        stock = product['stock']
        if stock == 0:
            out_of_stock.append(product)
        elif stock <= LOW_STOCK_THRESHOLD:
            low_stock.append(product)
        else:
            in_stock.append(product)

    # Print stock report
    print(f"\n📊 Stock Report — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   ✅ In Stock:     {len(in_stock)} products")
    print(f"   ⚠️  Low Stock:    {len(low_stock)} products")
    print(f"   🚫 Out of Stock: {len(out_of_stock)} products")

    # Send LOW STOCK alerts
    if low_stock:
        print(f"\n⚠️  LOW STOCK PRODUCTS:")
        for product in low_stock:
            product_id = product['id']
            last_alert_key = f"low_{product_id}"
            last_sent = last_alert_sent.get(last_alert_key, 0)

            print(f"   ⚠️  {product['name'][:50]}")
            print(f"       Stock: {product['stock']} remaining")

            if current_time - last_sent > ALERT_COOLDOWN:
                send_low_stock_alert(product['name'], product['stock'])
                last_alert_sent[last_alert_key] = current_time
                print(f"       📧 Alert email sent!")
            else:
                remaining = int((ALERT_COOLDOWN - (current_time - last_sent)) / 60)
                print(f"       ⏳ Alert cooldown: {remaining} mins remaining")

    # Send OUT OF STOCK alerts
    if out_of_stock:
        print(f"\n🚫 OUT OF STOCK PRODUCTS:")
        for product in out_of_stock:
            product_id = product['id']
            last_alert_key = f"out_{product_id}"
            last_sent = last_alert_sent.get(last_alert_key, 0)

            print(f"   🚫 {product['name'][:50]}")

            if current_time - last_sent > ALERT_COOLDOWN:
                send_out_of_stock_alert(product['name'])
                last_alert_sent[last_alert_key] = current_time
                print(f"       📧 Alert email sent!")
            else:
                remaining = int((ALERT_COOLDOWN - (current_time - last_sent)) / 60)
                print(f"       ⏳ Alert cooldown: {remaining} mins remaining")

    return out_of_stock, low_stock, in_stock


# ============================================================
# MAIN CONTINUOUS MONITORING LOOP
# ============================================================
print(f"\n🔄 Monitoring stock every {CHECK_INTERVAL} seconds")
print(f"⚠️  Alert threshold: {LOW_STOCK_THRESHOLD} items")
print(f"📧 Alert cooldown: {ALERT_COOLDOWN//3600} hour(s)")
print(f"\nPress Ctrl+C to stop")
print("="*50)

check_count = 0

try:
    while True:
        check_count += 1
        print(f"\n{'='*50}")
        print(f"🔍 Stock Check #{check_count} — {datetime.now().strftime('%H:%M:%S')}")

        # Get current stock from WooCommerce
        products = get_stock_levels()

        if not products:
            print("⚠️  No products with stock tracking found!")
        else:
            print(f"   Found {len(products)} products with stock tracking")

            # Save to PostgreSQL (no duplicates!)
            save_stock_to_postgres(products)

            # Check and send alerts
            out_of_stock, low_stock, in_stock = check_and_alert(products)

            if not low_stock and not out_of_stock:
                print(f"\n✅ All products well stocked!")

        print(f"\n⏳ Next check in {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)

except KeyboardInterrupt:
    print(f"\n\n{'='*50}")
    print("🛑 Stock Monitor Stopped")
    print(f"   Total checks: {check_count}")
    print("="*50)