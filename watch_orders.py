from kafka import KafkaProducer
import json
import time
import os
import subprocess
from collections import defaultdict
from postgres_connector import insert_order, get_connection

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

print("🚀 Watching for new WooCommerce orders...")
print("="*50)

last_order_id = None

# Track order velocity per customer email
order_times = defaultdict(list)


def is_new_customer(email):
    """Check PostgreSQL to determine if customer is new"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM orders
            WHERE customer_email = %s
        """, (email,))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        is_new = count <= 1
        print(f"   👤 Customer '{email}': {count} previous orders → {'NEW' if is_new else 'EXISTING'} customer")
        return is_new
    except Exception as e:
        print(f"   ⚠️ Could not check customer history: {e}")
        return True


while True:
    try:
        result = subprocess.run(
            ['docker', 'compose', '-f',
             os.path.expanduser('~/ecommerce-project/docker-compose.yml'),
             'exec', '-T', 'wordpress',
             'cat', '/var/www/html/wp-content/orders.json'],
            capture_output=True, text=True
        )

        if result.stdout:
            lines = result.stdout.strip().split('\n')
            latest_line = lines[-1]

            if latest_line:
                order = json.loads(latest_line)
                order_id = order.get('order_id')

                if order_id and order_id != last_order_id:
                    last_order_id = order_id

                    # Calculate real velocity
                    customer_email = order.get('email', 'unknown')
                    current_time = time.time()

                    # Remove orders older than 1 hour
                    order_times[customer_email] = [
                        t for t in order_times[customer_email]
                        if current_time - t < 3600
                    ]
                    order_times[customer_email].append(current_time)
                    velocity = len(order_times[customer_email])

                    # Check if new customer using PostgreSQL
                    new_customer = is_new_customer(customer_email)

                    kafka_order = {
                        "order_id": f"WOO-{order_id}",
                        "customer_email": customer_email,
                        "customer_name": f"{order.get('first_name', '')} {order.get('last_name', '')}",
                        "amount": float(order.get('total', 0)),
                        "quantity": sum(
                            i.get('quantity', 1)
                            for i in order.get('items', [])
                        ),
                        "payment_method": order.get('payment_method', 'unknown'),
                        "is_new_customer": new_customer,
                        "orders_last_hour": velocity,
                        "card_country": order.get('country', 'US'),
                        "shipping_country": order.get('country', 'US'),
                        "failed_attempts": 0,
                        "products": [
                            i.get('name')
                            for i in order.get('items', [])
                        ],
                        "timestamp": order.get('timestamp')
                    }

                    # Send to Kafka for fraud detection
                    producer.send('orders', value=kafka_order)
                    producer.flush()

                    print(f"\n📦 New order detected!")
                    print(f"   Order:       {kafka_order['order_id']}")
                    print(f"   Amount:      ${kafka_order['amount']}")
                    print(f"   Email:       {kafka_order['customer_email']}")
                    print(f"   New Customer:{kafka_order['is_new_customer']}")
                    print(f"   Velocity:    {velocity} orders in last hour")
                    print(f"   Items:       {[p[:30] for p in kafka_order['products']]}")
                    print(f"   Payment:     {kafka_order['payment_method']}")

                    if velocity > 3:
                        print(f"   🚨 VELOCITY ALERT: {velocity} orders in last hour!")

                    # Save to PostgreSQL
                    insert_order(kafka_order)
                    print(f"✅ Saved to PostgreSQL!")
                    # NOTE: Emails are sent by fraud_detector_ml.py
                    # after fraud check is complete
                    print(f"📨 Order sent to fraud detection for analysis...")
                    print("-"*50)

    except Exception as e:
        print(f"❌ Error: {str(e)}")

    time.sleep(3)