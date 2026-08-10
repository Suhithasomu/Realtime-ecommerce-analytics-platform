import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ============================================
# YOUR EMAIL SETTINGS
# ============================================
SENDER_EMAIL = "YOUR_EMAIL@gmail.com"
APP_PASSWORD = "YOUR_GMAIL_APP_PASSWORD"
ADMIN_EMAIL = "YOUR_EMAIL@gmail.com"


def send_email(to_email, subject, html_body):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Email failed: {str(e)}")
        return False


# ============================================
# Email 1 — Order Confirmation (to customer)
# ============================================
def send_order_confirmation(order):
    customer_email = order.get('customer_email', '')
    if not customer_email:
        return

    products_list = order.get('products', [])
    products = ', '.join([str(p) for p in products_list])[:100] if isinstance(products_list, list) else str(products_list)[:100]
    amount = float(order.get('amount', 0))
    order_id = order.get('order_id')
    payment = order.get('payment_method', 'unknown')

    subject = f"✅ Order Confirmed — {order_id}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #4CAF50; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">✅ Order Confirmed!</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2>Thank you for your order!</h2>
            <p>Hi there! Your order has been placed successfully.</p>
            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #4CAF50;">
                <h3 style="color: #4CAF50;">📦 Order Details</h3>
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Products:</strong> {products}</p>
                <p><strong>Amount:</strong> ${amount:,.2f}</p>
                <p><strong>Payment:</strong> {payment}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y %H:%M')}</p>
            </div>
            <p>Your order is being processed and will be delivered soon!</p>
            <p>Track your order: <a href="http://localhost:8080/my-account/orders">My Orders</a></p>
        </div>
        <div style="background: #333; padding: 20px; text-align: center;">
            <p style="color: white; margin: 0;">My Ecommerce Store | Powered by Real-Time Analytics</p>
        </div>
    </body>
    </html>
    """
    send_email(customer_email, subject, html)


# ============================================
# Email 2 — Order Under Review (to customer)
# ============================================
def send_order_under_review(order):
    customer_email = order.get('customer_email', '')
    if not customer_email:
        return

    products_list = order.get('products', [])
    products = ', '.join([str(p) for p in products_list])[:100] if isinstance(products_list, list) else str(products_list)[:100]
    amount = float(order.get('amount', 0))
    order_id = order.get('order_id')

    subject = f"⏳ Order Under Review — {order_id}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #FF9800; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">⏳ Order Under Review</h1>
        </div>
        <div style="padding: 30px; background: #fff8f0;">
            <h2>Your order is being reviewed</h2>
            <p>Hi there! Thank you for your order. Our security team is
               currently reviewing your order to ensure everything is in order.</p>
            <div style="background: white; padding: 20px; border-radius: 8px;
                        margin: 20px 0; border-left: 4px solid #FF9800;">
                <h3 style="color: #FF9800;">📦 Order Details</h3>
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Products:</strong> {products}</p>
                <p><strong>Amount:</strong> ${amount:,.2f}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%B %d, %Y %H:%M')}</p>
                <p><strong>Status:</strong>
                   <span style="color: #FF9800; font-weight: bold;">⏳ Under Review</span>
                </p>
            </div>
            <div style="background: #fff3e0; padding: 15px; border-radius: 8px;">
                <p>⏱️ <strong>What happens next?</strong></p>
                <p>Our team will review your order within 24 hours.
                   You will receive an update once the review is complete.</p>
                <p>If you have any questions please contact our support team.</p>
            </div>
        </div>
        <div style="background: #333; padding: 20px; text-align: center;">
            <p style="color: white; margin: 0;">My Ecommerce Store | Powered by Real-Time Analytics</p>
        </div>
    </body>
    </html>
    """
    send_email(customer_email, subject, html)


# ============================================
# Email 3 — Admin New Order Notification
# ============================================
def send_admin_order_notification(order):
    amount = float(order.get('amount', 0))
    order_id = order.get('order_id')
    customer_email = order.get('customer_email', '')
    products_list = order.get('products', [])
    products = ', '.join([str(p) for p in products_list])[:100] if isinstance(products_list, list) else str(products_list)[:100]
    payment = order.get('payment_method', 'unknown')

    subject = f"🛍️ New Order Received — {order_id} — ${amount:,.2f}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #2196F3; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">🛍️ New Order!</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2>New order received!</h2>
            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #2196F3;">
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Customer:</strong> {customer_email}</p>
                <p><strong>Products:</strong> {products}</p>
                <p><strong>Amount:</strong> ${amount:,.2f}</p>
                <p><strong>Payment:</strong> {payment}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%B %d, %Y %H:%M')}</p>
            </div>
            <p><a href="http://localhost:8080/wp-admin/edit.php?post_type=shop_order">View in WooCommerce Admin →</a></p>
        </div>
    </body>
    </html>
    """
    send_email(ADMIN_EMAIL, subject, html)


# ============================================
# Email 4 — Fraud Alert (to admin)
# ============================================
def send_fraud_alert(order, fraud_score, reasons):
    amount = float(order.get('amount', 0))
    order_id = order.get('order_id')
    customer_email = order.get('customer_email', '')
    reasons_html = ''.join([f"<li style='margin: 8px 0;'>⚠️ {r}</li>" for r in reasons])

    subject = f"🚨 FRAUD ALERT — {order_id} — Score: {fraud_score}/100"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #f44336; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">🚨 FRAUD DETECTED!</h1>
        </div>
        <div style="padding: 30px; background: #fff3f3;">
            <h2 style="color: #f44336;">Suspicious order flagged for review!</h2>
            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #f44336;">
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Customer:</strong> {customer_email}</p>
                <p><strong>Amount:</strong> ${amount:,.2f}</p>
                <p><strong>Fraud Score:</strong> <span style="color: #f44336; font-size: 18px; font-weight: bold;">{fraud_score}/100</span></p>
                <p><strong>Time:</strong> {datetime.now().strftime('%B %d, %Y %H:%M')}</p>
                <p><strong>Status:</strong> <span style="color: #FF9800;">⏸️ Order placed ON HOLD - Awaiting admin review</span></p>
            </div>
            <div style="background: #fff3f3; padding: 20px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #f44336;">
                <h3>🚨 Fraud Signals Detected:</h3>
                <ul style="list-style: none; padding: 0;">{reasons_html}</ul>
            </div>
            <div style="background: #e3f2fd; padding: 20px; border-radius: 8px; margin-top: 20px;">
                <h3 style="color: #1976D2;">👨‍💼 Admin Actions Required:</h3>
                <p>1. Review the order in WooCommerce</p>
                <p>2. If confirmed fraud → Cancel order (shows as "Admin Cancelled")</p>
                <p>3. If legitimate → Change status to "Processing"</p>
                <a href="http://localhost:8080/wp-admin/edit.php?post_type=shop_order&post_status=wc-on-hold"
                   style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-top: 10px;">
                   🔍 Review Order in Admin →
                </a>
            </div>
        </div>
        <div style="background: #333; padding: 20px; text-align: center;">
            <p style="color: white; margin: 0;">My Ecommerce Store | Real-Time Fraud Detection System</p>
        </div>
    </body>
    </html>
    """
    send_email(ADMIN_EMAIL, subject, html)


# ============================================
# Email 5 — Admin Cancelled Order
# ============================================
def send_admin_cancelled_email(order, reason="Suspicious activity detected"):
    customer_email = order.get('customer_email', '')
    order_id = order.get('order_id')
    amount = float(order.get('amount', 0))

    subject_customer = f"❌ Order Cancelled — {order_id}"
    html_customer = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #9C27B0; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">❌ Order Cancelled</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2>Your order has been cancelled</h2>
            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #9C27B0;">
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Amount:</strong> ${amount:,.2f}</p>
                <p><strong>Cancelled by:</strong> Store Administrator</p>
                <p><strong>Reason:</strong> {reason}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%B %d, %Y %H:%M')}</p>
            </div>
            <p>If you believe this was a mistake please contact our support team.</p>
        </div>
        <div style="background: #333; padding: 20px; text-align: center;">
            <p style="color: white; margin: 0;">My Ecommerce Store</p>
        </div>
    </body>
    </html>
    """

    subject_admin = f"👨‍💼 Admin Cancelled Order — {order_id}"
    html_admin = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #607D8B; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">👨‍💼 Order Admin Cancelled</h1>
        </div>
        <div style="padding: 30px; background: #f9f9f9;">
            <h2>Order cancelled by admin</h2>
            <div style="background: white; padding: 20px; border-radius: 8px;">
                <p><strong>Order ID:</strong> {order_id}</p>
                <p><strong>Customer:</strong> {customer_email}</p>
                <p><strong>Amount:</strong> ${amount:,.2f}</p>
                <p><strong>Reason:</strong> {reason}</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%B %d, %Y %H:%M')}</p>
                <p><strong>Status:</strong> Admin Cancelled ✅</p>
            </div>
        </div>
    </body>
    </html>
    """

    if customer_email:
        send_email(customer_email, subject_customer, html_customer)
    send_email(ADMIN_EMAIL, subject_admin, html_admin)


# ============================================
# Email 6 — Low Stock Alert (to admin)
# ============================================
def send_low_stock_alert(product_name, stock_level):
    subject = f"⚠️ Low Stock Alert — {product_name[:40]}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #FF9800; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">⚠️ Low Stock Alert!</h1>
        </div>
        <div style="padding: 30px; background: #fff8f0;">
            <h2>Product running low!</h2>
            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #FF9800;">
                <p><strong>Product:</strong> {product_name}</p>
                <p><strong>Stock Level:</strong> {stock_level} remaining</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%B %d, %Y %H:%M')}</p>
                <p style="color: #FF9800;"><strong>Action needed: Restock soon!</strong></p>
            </div>
        </div>
    </body>
    </html>
    """
    send_email(ADMIN_EMAIL, subject, html)


# ============================================
# Email 7 — Out of Stock (to admin)
# ============================================
def send_out_of_stock_alert(product_name):
    subject = f"🚫 OUT OF STOCK — {product_name[:40]}"
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: #9C27B0; padding: 20px; text-align: center;">
            <h1 style="color: white; margin: 0;">🚫 Out of Stock!</h1>
        </div>
        <div style="padding: 30px; background: #f9f0ff;">
            <h2>Product is out of stock!</h2>
            <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #9C27B0;">
                <p><strong>Product:</strong> {product_name}</p>
                <p><strong>Stock Level:</strong> 0 remaining</p>
                <p><strong>Time:</strong> {datetime.now().strftime('%B %d, %Y %H:%M')}</p>
                <p style="color: #9C27B0;"><strong>Action needed: Restock immediately!</strong></p>
            </div>
        </div>
    </body>
    </html>
    """
    send_email(ADMIN_EMAIL, subject, html)


# ============================================
# Test all emails
# ============================================
if __name__ == "__main__":
    print("🧪 Testing email alerts...")
    print("="*50)

    test_order = {
        "order_id": "WOO-999",
        "customer_email": ADMIN_EMAIL,
        "amount": 999.99,
        "products": ["Apple MacBook Air M2"],
        "payment_method": "stripe"
    }

    print("\n1. Testing order confirmation...")
    send_order_confirmation(test_order)

    print("\n2. Testing order under review...")
    send_order_under_review(test_order)

    print("\n3. Testing admin notification...")
    send_admin_order_notification(test_order)

    print("\n4. Testing fraud alert...")
    send_fraud_alert(test_order, fraud_score=85, reasons=[
        "High amount + new customer",
        "Card country mismatch",
        "Multiple failed attempts"
    ])

    print("\n5. Testing admin cancelled...")
    send_admin_cancelled_email(test_order, "Confirmed fraudulent order")

    print("\n6. Testing low stock alert...")
    send_low_stock_alert("Apple MacBook Air M2", 3)

    print("\n7. Testing out of stock alert...")
    send_out_of_stock_alert("Sony WH-1000XM5 Headphones")

    print("\n" + "="*50)
    print("🎉 All email tests complete!")
    print("Check your inbox at:", ADMIN_EMAIL)