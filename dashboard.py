import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import json
import subprocess
import time
from datetime import datetime
from postgres_connector import get_connection

st.set_page_config(
    page_title="Real-Time E-Commerce Analytics",
    page_icon="🛍️",
    layout="wide"
)

st.title("🛍️ Real-Time E-Commerce Analytics Dashboard")
st.markdown("**Live fraud detection • Sentiment analysis • Recommendations • Stock monitoring • Powered by Kafka & PostgreSQL**")

# ============================================================
# DATA FUNCTIONS
# ============================================================

def get_orders_from_file():
    try:
        result = subprocess.run(
            ['docker', 'compose', '-f',
             '/Users/suhitha/ecommerce-project/docker-compose.yml',
             'exec', '-T', 'wordpress',
             'cat', '/var/www/html/wp-content/orders.json'],
            capture_output=True, text=True
        )
        orders = []
        seen_ids = set()
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        order = json.loads(line)
                        order_id = order.get('order_id')
                        if order_id not in seen_ids:
                            seen_ids.add(order_id)
                            orders.append(order)
                    except:
                        pass
        return orders
    except:
        return []

def get_sentiment_from_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT product_name, final_sentiment,
                   COUNT(*) as review_count,
                   ROUND(AVG(vader_score)::numeric, 3) as avg_score
            FROM product_reviews
            GROUP BY product_name, final_sentiment
            ORDER BY product_name, COUNT(*) DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return pd.DataFrame(rows, columns=['Product', 'Sentiment', 'Count', 'Avg Score'])
    except:
        return pd.DataFrame()

def get_fraud_scores_from_db():
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT order_id, customer_email, amount,
                   rule_score, ml_score, final_score,
                   status, created_at
            FROM fraud_scores
            ORDER BY created_at DESC LIMIT 20
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return pd.DataFrame(rows, columns=[
            'Order ID', 'Email', 'Amount',
            'Rule Score', 'ML Score', 'Final Score',
            'Status', 'Time'
        ])
    except:
        return pd.DataFrame()

def get_recommendations_from_db(product_name=None):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if product_name:
            cursor.execute("""
                SELECT source_product, recommended_product,
                       category, price, similarity_score, rank
                FROM recommendations
                WHERE source_product ILIKE %s
                ORDER BY rank ASC LIMIT 5
            """, (f"%{product_name}%",))
        else:
            cursor.execute("""
                SELECT source_product, recommended_product,
                       category, price, similarity_score, rank
                FROM recommendations
                ORDER BY similarity_score DESC LIMIT 50
            """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return pd.DataFrame(rows, columns=[
            'Source Product', 'Recommended Product',
            'Category', 'Price', 'Similarity Score', 'Rank'
        ])
    except:
        return pd.DataFrame()

def get_stock_from_db():
    """Get latest stock levels from PostgreSQL"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        # Get latest stock entry per product
        cursor.execute("""
            SELECT DISTINCT ON (product_name)
                product_name,
                stock_level,
                status,
                checked_at
            FROM stock_levels
            ORDER BY product_name, checked_at DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return pd.DataFrame(rows, columns=[
            'Product', 'Stock Level', 'Status', 'Last Checked'
        ])
    except:
        return pd.DataFrame()

def get_stock_live():
    """Get LIVE stock from WooCommerce right now"""
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
    if($stock !== null) {
        echo $id . "|" . $stock . "|" . $name . "\n";
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
                    parts = line.split('|', 2)
                    if len(parts) == 3:
                        try:
                            stock = int(parts[1]) if parts[1].strip().lstrip('-').isdigit() else 0
                            if stock == 0:
                                status = '🚫 OUT OF STOCK'
                            elif stock <= 5:
                                status = '⚠️ LOW STOCK'
                            else:
                                status = '✅ IN STOCK'
                            products.append({
                                'Product': parts[2].strip()[:60],
                                'Stock': stock,
                                'Status': status
                            })
                        except:
                            pass
        return pd.DataFrame(products) if products else pd.DataFrame()
    except:
        return pd.DataFrame()

def check_is_new_customer(email):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders WHERE customer_email = %s", (email,))
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count <= 1
    except:
        return True

def calculate_fraud_score(order):
    score = 0
    reasons = []
    amount = float(order.get('total', 0))
    payment = order.get('payment_method', '')
    country = order.get('country', 'US')
    email = order.get('email', '')
    quantity = sum(i.get('quantity', 1) for i in order.get('items', []))
    is_new = check_is_new_customer(email)

    if amount > 1000 and is_new:
        score += 40
        reasons.append("High amount + new customer")
    if amount > 1500:
        score += 30
        reasons.append("Very high amount")
    if quantity > 3:
        score += 30
        reasons.append(f"High quantity {quantity} items")
    if payment == 'stripe' and amount > 500 and is_new:
        score += 35
        reasons.append("High card payment + new customer")
    if country not in ['US', 'CA', 'GB', 'AU']:
        score += 25
        reasons.append("International order")
    if amount % 100 == 0 and amount > 500:
        score += 15
        reasons.append("Suspicious round amount")
    if payment == 'stripe' and is_new:
        score += 20
        reasons.append("Card payment from new customer")
    if amount > 1500:
        score += 45
        reasons.append(f"Extremely high order value ${amount}")
    if quantity >= 3 and amount > 500:
        score += 40
        reasons.append(f"Bulk purchase {quantity} items worth ${amount}")

    if score >= 55:
        status = "🚨 FRAUD"
        color = "#EF553B"
    elif score >= 31:
        status = "⚠️ REVIEW"
        color = "#FFA15A"
    else:
        status = "✅ APPROVED"
        color = "#00CC96"

    return score, status, color, reasons

# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.title("⚙️ Settings")
refresh = st.sidebar.slider("Refresh (seconds)", 3, 30, 5)
page = st.sidebar.radio(
    "Navigate",
    ["📊 Overview", "🚨 Fraud Detection",
     "🎭 Sentiment Analysis", "🛍️ Recommendations",
     "📦 Stock Monitor"]
)
st.sidebar.markdown("---")
st.sidebar.markdown("### 🟢 System Status")
st.sidebar.success("✅ Kafka Running")
st.sidebar.success("✅ Fraud Detector Active")
st.sidebar.success("✅ PostgreSQL Connected")
st.sidebar.success("✅ Stock Monitor Active")
st.sidebar.success("✅ Store Online")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🃏 Test Cards")
st.sidebar.code("✅ 4242 4242 4242 4242")
st.sidebar.code("❌ 4000 0000 0000 0002")

placeholder = st.empty()
iteration = 0

while True:
    iteration += 1
    orders = get_orders_from_file()
    fraud_df = get_fraud_scores_from_db()
    sentiment_df = get_sentiment_from_db()

    with placeholder.container():

        # ============================================================
        # PAGE 1: OVERVIEW
        # ============================================================
        if page == "📊 Overview":
            st.header("📊 Store Overview")
            if not orders:
                st.warning("⏳ No orders yet! Place an order at http://localhost:8080/shop")
            else:
                fraud_data = [calculate_fraud_score(o) for o in orders]
                total_revenue = sum(float(o.get('total', 0)) for o in orders)
                total_orders = len(orders)
                fraud_count = sum(1 for _, s, _, _ in fraud_data if "FRAUD" in s)
                approved_count = sum(1 for _, s, _, _ in fraud_data if "APPROVED" in s)
                review_count = sum(1 for _, s, _, _ in fraud_data if "REVIEW" in s)

                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.metric("💰 Revenue", f"${total_revenue:,.2f}")
                with col2:
                    st.metric("📦 Orders", total_orders)
                with col3:
                    st.metric("✅ Approved", approved_count)
                with col4:
                    st.metric("⚠️ Review", review_count)
                with col5:
                    st.metric("🚨 Blocked", fraud_count)

                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📊 Order Status")
                    fig1 = px.pie(
                        values=[approved_count, review_count, fraud_count],
                        names=["Approved", "Review", "Fraud"],
                        color_discrete_map={
                            "Approved": "#00CC96",
                            "Review": "#FFA15A",
                            "Fraud": "#EF553B"
                        }
                    )
                    st.plotly_chart(fig1, key=f"pie_{iteration}", use_container_width=True)
                with col2:
                    st.subheader("💰 Revenue by Payment")
                    payment_data = {}
                    for order in orders:
                        payment = order.get('payment_method', 'unknown')
                        amount = float(order.get('total', 0))
                        payment_data[payment] = payment_data.get(payment, 0) + amount
                    fig2 = px.bar(
                        x=list(payment_data.keys()),
                        y=list(payment_data.values()),
                        labels={"x": "Payment", "y": "Revenue ($)"},
                        color=list(payment_data.keys())
                    )
                    st.plotly_chart(fig2, key=f"bar_{iteration}", use_container_width=True)

                st.markdown("---")
                st.subheader("📋 Recent Orders")
                table_data = []
                for order, (score, status, color, reasons) in zip(orders, fraud_data):
                    items = [i.get('name', '')[:25] for i in order.get('items', [])]
                    table_data.append({
                        "Order": f"WOO-{order.get('order_id')}",
                        "Email": order.get('email', 'unknown'),
                        "Amount": f"${float(order.get('total', 0)):,.2f}",
                        "Payment": order.get('payment_method', 'unknown'),
                        "Items": ', '.join(items)[:40],
                        "Score": f"{score}/100",
                        "Status": status
                    })
                st.dataframe(pd.DataFrame(table_data), use_container_width=True, height=300)

        # ============================================================
        # PAGE 2: FRAUD DETECTION
        # ============================================================
        elif page == "🚨 Fraud Detection":
            st.header("🚨 Fraud Detection Center")
            if orders:
                latest_order = orders[-1]
                latest_score, latest_status, latest_color, latest_reasons = calculate_fraud_score(latest_order)
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🎯 Latest Order Analysis")
                    fig3 = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=latest_score,
                        title={"text": "Fraud Risk Score"},
                        gauge={
                            "axis": {"range": [0, 200]},
                            "bar": {"color": latest_color},
                            "steps": [
                                {"range": [0, 31], "color": "#e8f5e9"},
                                {"range": [31, 55], "color": "#fff3e0"},
                                {"range": [55, 200], "color": "#ffebee"}
                            ],
                            "threshold": {
                                "line": {"color": "red", "width": 4},
                                "thickness": 0.75,
                                "value": 55
                            }
                        }
                    ))
                    st.plotly_chart(fig3, key=f"gauge_{iteration}", use_container_width=True)
                with col2:
                    st.markdown(f"### {latest_status}")
                    st.markdown(f"**Order:** WOO-{latest_order.get('order_id')}")
                    st.markdown(f"**Amount:** ${float(latest_order.get('total', 0)):,.2f}")
                    st.markdown(f"**Payment:** {latest_order.get('payment_method')}")
                    st.markdown(f"**Email:** {latest_order.get('email')}")
                    is_new = check_is_new_customer(latest_order.get('email', ''))
                    st.markdown(f"**New Customer:** {'Yes ⚠️' if is_new else 'No ✅'}")
                    if latest_reasons:
                        st.markdown("**🚨 Fraud Signals:**")
                        for r in latest_reasons:
                            st.warning(f"⚠️ {r}")
                    else:
                        st.success("✅ No fraud signals!")

            st.markdown("---")
            if not fraud_df.empty:
                st.subheader("📋 Fraud Scores from PostgreSQL")
                st.dataframe(fraud_df, use_container_width=True, height=300)
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("🎯 Score Distribution")
                    fig4 = px.histogram(fraud_df, x="Final Score", color="Status", nbins=20)
                    st.plotly_chart(fig4, key=f"hist_{iteration}", use_container_width=True)
                with col2:
                    st.subheader("📊 Status Breakdown")
                    status_counts = fraud_df['Status'].value_counts()
                    fig5 = px.pie(values=status_counts.values, names=status_counts.index)
                    st.plotly_chart(fig5, key=f"pie2_{iteration}", use_container_width=True)
            else:
                st.info("No fraud scores yet — place orders to see data!")

        # ============================================================
        # PAGE 3: SENTIMENT ANALYSIS
        # ============================================================
        elif page == "🎭 Sentiment Analysis":
            st.header("🎭 Product Sentiment Analysis")

            if sentiment_df.empty:
                st.warning("⏳ No sentiment data yet! Run: python3 sentiment_all_products.py")
            else:
                total_reviews = sentiment_df['Count'].sum()
                positive = sentiment_df[sentiment_df['Sentiment']=='POSITIVE']['Count'].sum()
                negative = sentiment_df[sentiment_df['Sentiment']=='NEGATIVE']['Count'].sum()
                neutral = sentiment_df[sentiment_df['Sentiment']=='NEUTRAL']['Count'].sum()

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📝 Total Reviews", int(total_reviews))
                with col2:
                    st.metric("✅ Positive", int(positive))
                with col3:
                    st.metric("❌ Negative", int(negative))
                with col4:
                    st.metric("😐 Neutral", int(neutral))

                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("📊 Overall Sentiment")
                    fig6 = px.pie(
                        values=[positive, negative, neutral],
                        names=["Positive", "Negative", "Neutral"],
                        color_discrete_map={
                            "Positive": "#00CC96",
                            "Negative": "#EF553B",
                            "Neutral": "#636EFA"
                        }
                    )
                    st.plotly_chart(fig6, key=f"sent_pie_{iteration}", use_container_width=True)
                with col2:
                    st.subheader("🏆 Products by Sentiment")
                    product_sentiment = sentiment_df.pivot_table(
                        index='Product',
                        columns='Sentiment',
                        values='Count',
                        fill_value=0
                    ).reset_index()
                    product_sentiment['Product'] = product_sentiment['Product'].str[:25]
                    fig7 = px.bar(
                        product_sentiment,
                        x='Product',
                        y=[c for c in ['POSITIVE', 'NEGATIVE', 'NEUTRAL'] if c in product_sentiment.columns],
                        color_discrete_map={
                            "POSITIVE": "#00CC96",
                            "NEGATIVE": "#EF553B",
                            "NEUTRAL": "#636EFA"
                        },
                        barmode='stack'
                    )
                    fig7.update_xaxes(tickangle=45)
                    st.plotly_chart(fig7, key=f"sent_bar_{iteration}", use_container_width=True)

                st.markdown("---")
                st.subheader("📋 Product Sentiment Summary")
                summary = sentiment_df.sort_values('Count', ascending=False)
                summary = summary.drop_duplicates(subset=['Product'], keep='first')
                summary['Product'] = summary['Product'].str[:50]
                st.dataframe(
                    summary[['Product', 'Sentiment', 'Count', 'Avg Score']],
                    use_container_width=True, height=400
                )

        # ============================================================
        # PAGE 4: RECOMMENDATIONS
        # ============================================================
        elif page == "🛍️ Recommendations":
            st.header("🛍️ Product Recommendation Engine")
            st.markdown("**Content-based filtering using TF-IDF + Cosine Similarity**")

            search_term = st.text_input(
                "🔍 Search product:",
                placeholder="e.g. MacBook, headphones, gaming...",
                key=f"product_search_{iteration}"
            )

            if search_term:
                rec_df = get_recommendations_from_db(search_term)
                if not rec_df.empty:
                    st.subheader(f"🎯 Top recommendations for '{search_term}':")
                    for _, row in rec_df.iterrows():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"**{row['Rank']}. {row['Recommended Product'][:60]}**")
                        with col2:
                            st.markdown(f"💰 ${row['Price']}")
                        with col3:
                            score = float(row['Similarity Score'])
                            if score > 50:
                                st.success(f"Match: {score:.0f}%")
                            elif score > 20:
                                st.warning(f"Match: {score:.0f}%")
                            else:
                                st.info(f"Match: {score:.0f}%")

                    st.markdown("---")
                    rec_df['Short Name'] = rec_df['Recommended Product'].str[:30]
                    fig8 = px.bar(
                        rec_df,
                        x='Similarity Score',
                        y='Short Name',
                        orientation='h',
                        color='Similarity Score',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig8, key=f"rec_bar_{iteration}", use_container_width=True)
                else:
                    st.warning(f"No recommendations found for '{search_term}'")
            else:
                all_recs = get_recommendations_from_db()
                if not all_recs.empty:
                    st.subheader("📊 Top Product Recommendations")
                    top_recs = all_recs.nlargest(10, 'Similarity Score')
                    top_recs['Source'] = top_recs['Source Product'].str[:25]
                    top_recs['Recommended'] = top_recs['Recommended Product'].str[:25]
                    fig9 = px.scatter(
                        top_recs,
                        x='Source',
                        y='Recommended',
                        size='Similarity Score',
                        color='Similarity Score',
                        color_continuous_scale='Viridis'
                    )
                    fig9.update_xaxes(tickangle=45)
                    st.plotly_chart(fig9, key=f"rec_scatter_{iteration}", use_container_width=True)
                    st.markdown("---")
                    st.subheader("📋 All Recommendations")
                    st.dataframe(all_recs, use_container_width=True, height=400)
                else:
                    st.info("⏳ Run: python3 recommendation_system.py")

        # ============================================================
        # PAGE 5: STOCK MONITOR
        # ============================================================
        elif page == "📦 Stock Monitor":
            st.header("📦 Real-Time Stock Monitor")
            st.markdown("**Live inventory tracking with automatic email alerts**")

            # Get live stock from WooCommerce
            stock_live_df = get_stock_live()
            # Get history from PostgreSQL
            stock_db_df = get_stock_from_db()

            if stock_live_df.empty:
                st.warning("""
                ⚠️ No stock data found!

                To enable stock tracking:
                1. Go to http://localhost:8080/wp-admin
                2. Edit any product
                3. Click **Inventory** tab
                4. Check **Enable stock management**
                5. Set a stock quantity
                6. Click **Update**
                """)
            else:
                # Stock summary metrics
                total = len(stock_live_df)
                in_stock = len(stock_live_df[stock_live_df['Status'] == '✅ IN STOCK'])
                low_stock = len(stock_live_df[stock_live_df['Status'] == '⚠️ LOW STOCK'])
                out_of_stock = len(stock_live_df[stock_live_df['Status'] == '🚫 OUT OF STOCK'])

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 Total Products", total)
                with col2:
                    st.metric("✅ In Stock", in_stock)
                with col3:
                    st.metric("⚠️ Low Stock", low_stock,
                             delta=f"-{low_stock}" if low_stock > 0 else None,
                             delta_color="inverse")
                with col4:
                    st.metric("🚫 Out of Stock", out_of_stock,
                             delta=f"-{out_of_stock}" if out_of_stock > 0 else None,
                             delta_color="inverse")

                st.markdown("---")

                # Alert banners
                if out_of_stock > 0:
                    out_products = stock_live_df[stock_live_df['Status'] == '🚫 OUT OF STOCK']
                    for _, row in out_products.iterrows():
                        st.error(f"🚫 OUT OF STOCK: **{row['Product']}** — Restock immediately! 📧 Alert sent!")

                if low_stock > 0:
                    low_products = stock_live_df[stock_live_df['Status'] == '⚠️ LOW STOCK']
                    for _, row in low_products.iterrows():
                        st.warning(f"⚠️ LOW STOCK: **{row['Product']}** — Only **{row['Stock']}** left! 📧 Alert sent!")

                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("📊 Stock Status Distribution")
                    status_counts = stock_live_df['Status'].value_counts()
                    fig_stock1 = px.pie(
                        values=status_counts.values,
                        names=status_counts.index,
                        color=status_counts.index,
                        color_discrete_map={
                            '✅ IN STOCK': '#00CC96',
                            '⚠️ LOW STOCK': '#FFA15A',
                            '🚫 OUT OF STOCK': '#EF553B'
                        }
                    )
                    st.plotly_chart(fig_stock1, key=f"stock_pie_{iteration}", use_container_width=True)

                with col2:
                    st.subheader("📦 Stock Levels by Product")
                    # Show top 10 lowest stock products
                    low_products_df = stock_live_df.nsmallest(10, 'Stock')
                    fig_stock2 = px.bar(
                        low_products_df,
                        x='Stock',
                        y='Product',
                        orientation='h',
                        color='Status',
                        color_discrete_map={
                            '✅ IN STOCK': '#00CC96',
                            '⚠️ LOW STOCK': '#FFA15A',
                            '🚫 OUT OF STOCK': '#EF553B'
                        }
                    )
                    fig_stock2.add_vline(
                        x=5, line_dash="dash",
                        line_color="orange",
                        annotation_text="Low Stock Threshold (5)"
                    )
                    st.plotly_chart(fig_stock2, key=f"stock_bar_{iteration}", use_container_width=True)

                st.markdown("---")
                st.subheader("📋 Complete Stock List")

                # Color code the dataframe
                def color_status(val):
                    if 'OUT OF STOCK' in str(val):
                        return 'background-color: #ffebee; color: #c62828'
                    elif 'LOW STOCK' in str(val):
                        return 'background-color: #fff3e0; color: #e65100'
                    else:
                        return 'background-color: #e8f5e9; color: #1b5e20'

                styled_df = stock_live_df.style.map(
                    color_status, subset=['Status']
                )
                st.dataframe(styled_df, use_container_width=True, height=400)

                st.markdown("---")
                st.subheader("📧 Email Alert Configuration")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info("⚠️ **Low Stock Alert**\nSent when stock ≤ 5 items\nCooldown: 1 hour")
                with col2:
                    st.error("🚫 **Out of Stock Alert**\nSent when stock = 0\nCooldown: 1 hour")
                with col3:
                    st.success("✅ **Check Frequency**\nEvery 60 seconds\nSaves to PostgreSQL")

                if not stock_db_df.empty:
                    st.markdown("---")
                    st.subheader("📊 Stock History (PostgreSQL)")
                    st.dataframe(stock_db_df, use_container_width=True, height=200)

        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')} | Refreshing every {refresh}s")

    time.sleep(refresh)