from kafka import KafkaConsumer, KafkaProducer
from postgres_connector import insert_fraud_score
from email_alerts import (
    send_fraud_alert,
    send_order_confirmation,
    send_admin_order_notification,
    send_order_under_review
)
import json
import joblib
import numpy as np
from datetime import datetime
import subprocess

DOCKER_COMPOSE = '/Users/suhitha/ecommerce-project/docker-compose.yml'

# Load ML model
print("🤖 Loading ML fraud model...")
model = joblib.load('fraud_model.pkl')
scaler_amount = joblib.load('scaler_amount.pkl')
scaler_time = joblib.load('scaler_time.pkl')
print("✅ ML model loaded!")

consumer = KafkaConsumer(
    'orders',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8')),
    auto_offset_reset='latest',
    group_id='fraud-detector-ml'
)

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

print("🚀 ML Fraud Detector running!")
print("="*50)
print("Waiting for orders...")


def hold_order_in_woocommerce(order_id, reason="Fraud detected by ML system"):
    """Put order on hold in WooCommerce for admin review"""
    try:
        # Extract numeric order ID from WOO-123 format
        numeric_id = str(order_id).replace('WOO-', '').strip()

        php_code = f"""
// Try to find by exact ID first
$order = wc_get_order({numeric_id});
if($order) {{
    $order->update_status('on-hold', '{reason}. Pending admin review.');
    echo 'Order ' . $order->get_id() . ' put on hold';
}} else {{
    // Fallback: get most recent order
    $orders = wc_get_orders(array('limit' => 1, 'orderby' => 'date', 'order' => 'DESC'));
    if(!empty($orders)) {{
        $orders[0]->update_status('on-hold', '{reason}. Pending admin review.');
        echo 'Order ' . $orders[0]->get_id() . ' put on hold (fallback)';
    }} else {{
        echo 'No order found';
    }}
}}
"""
        result = subprocess.run(
            ['docker', 'compose', '-f', DOCKER_COMPOSE,
             'exec', '-T', 'wordpress',
             'php', 'wp-cli.phar', 'eval', php_code, '--allow-root'],
            capture_output=True, text=True
        )
        print(f"   🔒 WooCommerce: {result.stdout.strip()}")
    except Exception as e:
        print(f"   ⚠️ WooCommerce update failed: {e}")


def rule_based_score(order):
    score = 0
    reasons = []
    amount = float(order.get('amount', 0))
    is_new = order.get('is_new_customer', True)
    payment = order.get('payment_method', '')
    card_country = order.get('card_country', 'US')
    shipping_country = order.get('shipping_country', 'US')
    quantity = int(order.get('quantity', 1))
    velocity = int(order.get('orders_last_hour', 0))
    failed = int(order.get('failed_attempts', 0))

    if amount > 1000 and is_new:
        score += 40
        reasons.append(f"High amount ${amount} + new customer")
    if amount > 1500:
        score += 30
        reasons.append(f"Very high amount ${amount}")
    if quantity > 3:
        score += 30
        reasons.append(f"High quantity {quantity}")
    if velocity > 3:
        score += 50
        reasons.append(f"Too many orders: {velocity}/hour")
    if card_country != shipping_country:
        score += 35
        reasons.append(f"Country mismatch: {card_country} vs {shipping_country}")
    if failed > 2:
        score += 40
        reasons.append(f"Failed attempts: {failed}")
    if payment == 'stripe' and amount > 500 and is_new:
        score += 35
        reasons.append("High card payment + new customer")
    if payment == 'stripe' and is_new:
        score += 20
        reasons.append("Card payment from new customer")
    if amount % 100 == 0 and amount > 500:
        score += 15
        reasons.append(f"Suspicious round amount ${amount}")
    if amount > 1500:
        score += 45
        reasons.append(f"Extremely high order value ${amount}")
    if quantity >= 3 and amount > 500:
        score += 40
        reasons.append(f"Bulk purchase {quantity} items worth ${amount}")

    return score, reasons


def ml_score(order):
    try:
        amount = float(order.get('amount', 0))
        hour = datetime.now().hour
        time_seconds = hour * 3600

        amount_scaled = scaler_amount.transform([[amount]])[0][0]
        time_scaled = scaler_time.transform([[time_seconds]])[0][0]

        features = [time_scaled] + [0.0] * 28 + [amount_scaled]

        is_new = order.get('is_new_customer', True)
        velocity = int(order.get('orders_last_hour', 0))
        failed = int(order.get('failed_attempts', 0))

        if is_new:
            features[1] = -2.5
        if velocity > 3:
            features[2] = -3.0
        if failed > 2:
            features[3] = -2.8
        if amount > 1000:
            features[4] = -2.2

        features_array = np.array(features).reshape(1, -1)
        fraud_prob = model.predict_proba(features_array)[0][1]
        return int(fraud_prob * 100)

    except Exception as e:
        print(f"⚠️ ML scoring error: {str(e)}")
        return 0


for message in consumer:
    order = message.value
    print(f"\n📦 New order received!")
    print(f"   Order:   {order.get('order_id')}")
    print(f"   Email:   {order.get('customer_email')}")
    print(f"   Amount:  ${order.get('amount')}")
    print(f"   Payment: {order.get('payment_method')}")

    # Rule based score
    rule_score, reasons = rule_based_score(order)
    print(f"\n📏 Rule Score: {rule_score}/100")
    for r in reasons:
        print(f"   ⚠️ {r}")

    # ML score
    ml_fraud_score = ml_score(order)
    print(f"🤖 ML Score: {ml_fraud_score}/100")

    # Combined score
    final_score = max(rule_score, int(rule_score * 0.8 + ml_fraud_score * 0.2))
    print(f"🎯 Final Score: {final_score}/100")

    # Decision
    if final_score >= 55 or rule_score >= 55:
        status = "FRAUD_BLOCKED"
        emoji = "🚨"
        decision = "FRAUD DETECTED! Order BLOCKED!"
    elif final_score >= 31:
        status = "REVIEW_NEEDED"
        emoji = "⚠️"
        decision = "SUSPICIOUS! Flagged for review!"
    else:
        status = "APPROVED"
        emoji = "✅"
        decision = "Order APPROVED!"

    print(f"\n{emoji} {decision}")

    # Send to Kafka
    alert = {
        "order_id": order.get('order_id'),
        "customer_email": order.get('customer_email'),
        "amount": order.get('amount'),
        "rule_score": rule_score,
        "ml_score": ml_fraud_score,
        "final_score": final_score,
        "status": status,
        "reasons": reasons,
        "timestamp": datetime.now().isoformat()
    }
    producer.send('fraud-alerts', value=alert)
    print(f"📤 Result sent to Kafka!")

    if status == "FRAUD_BLOCKED":
        # Admin gets fraud alert
        send_fraud_alert(order, final_score, reasons)
        # Order goes ON HOLD in WooCommerce
        hold_order_in_woocommerce(
            order.get('order_id'),
            f"FRAUD DETECTED - Score: {final_score}/100"
        )
        # Customer gets "under review" email (not "confirmed")
        send_order_under_review(order)
        print("   🔒 Order put ON HOLD in WooCommerce")
        print("   📧 Fraud alert sent to admin")
        print("   📧 Under review email sent to customer")

    elif status == "REVIEW_NEEDED":
        # Admin gets review alert
        send_fraud_alert(order, final_score, reasons)
        # Order goes ON HOLD
        hold_order_in_woocommerce(
            order.get('order_id'),
            f"REVIEW NEEDED - Score: {final_score}/100"
        )
        # Customer gets "under review" email
        send_order_under_review(order)
        print("   🔒 Order put ON HOLD for review")
        print("   📧 Review alert sent to admin")
        print("   📧 Under review email sent to customer")

    else:
        # Normal approved order
        # Send confirmation to customer
        send_order_confirmation(order)
        # Send notification to admin
        send_admin_order_notification(order)
        print("   📧 Confirmation sent to customer")
        print("   📧 Admin notification sent")

    # Save to PostgreSQL
    insert_fraud_score(alert)

    print("="*50)
    print("Waiting for next order...")