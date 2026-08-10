#!/bin/bash

# ============================================================
# E-COMMERCE ANALYTICS - MASTER STARTUP SCRIPT
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   🛍️  E-COMMERCE ANALYTICS SYSTEM - STARTING UP${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

PROJECT_DIR=~/ecommerce-project
cd $PROJECT_DIR

# ============================================================
# STEP 1: Start Docker Services
# ============================================================
echo -e "${YELLOW}[1/6] Starting Docker services...${NC}"

if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running! Please start Docker Desktop first.${NC}"
    exit 1
fi

docker-compose up -d
echo -e "${YELLOW}   Waiting for services to be ready (15 seconds)...${NC}"
sleep 15

docker ps | grep -q "kafka"     && echo -e "${GREEN}   ✅ Kafka running${NC}"      || echo -e "${RED}   ❌ Kafka failed${NC}"
docker ps | grep -q "postgres"  && echo -e "${GREEN}   ✅ PostgreSQL running${NC}" || echo -e "${RED}   ❌ PostgreSQL failed${NC}"
docker ps | grep -q "wordpress" && echo -e "${GREEN}   ✅ WordPress running${NC}"  || echo -e "${RED}   ❌ WordPress failed${NC}"
echo ""

# ============================================================
# STEP 2: Activate Virtual Environment
# ============================================================
echo -e "${YELLOW}[2/6] Activating Python environment...${NC}"

if [ -d "venv" ]; then
    source venv/bin/activate
    echo -e "${GREEN}   ✅ Virtual environment activated${NC}"
else
    echo -e "${RED}   ❌ Virtual environment not found!${NC}"
    exit 1
fi
echo ""

# ============================================================
# STEP 3: Test PostgreSQL Connection
# ============================================================
echo -e "${YELLOW}[3/6] Testing PostgreSQL connection...${NC}"

python3 -c "from postgres_connector import test_connection; test_connection()" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}   ⚠️  Waiting 10 more seconds for PostgreSQL...${NC}"
    sleep 10
    python3 -c "from postgres_connector import test_connection; test_connection()" 2>/dev/null
fi
echo ""

# ============================================================
# STEP 4: Create Logs Directory
# ============================================================
mkdir -p logs

# ============================================================
# STEP 5: Start Background Services
# ============================================================
echo -e "${YELLOW}[4/6] Starting analytics services...${NC}"

# Start Order Watcher
echo -e "${YELLOW}   Starting Order Watcher...${NC}"
nohup python3 watch_orders.py > logs/watch_orders.log 2>&1 &
WATCH_PID=$!
echo $WATCH_PID > logs/watch_orders.pid
sleep 2
ps -p $WATCH_PID > /dev/null && \
    echo -e "${GREEN}   ✅ Order Watcher started (PID: $WATCH_PID)${NC}" || \
    echo -e "${RED}   ❌ Order Watcher failed - check logs/watch_orders.log${NC}"

# Start Fraud Detector
echo -e "${YELLOW}   Starting Fraud Detector...${NC}"
nohup python3 fraud_detector_ml.py > logs/fraud_detector.log 2>&1 &
FRAUD_PID=$!
echo $FRAUD_PID > logs/fraud_detector.pid
sleep 2
ps -p $FRAUD_PID > /dev/null && \
    echo -e "${GREEN}   ✅ Fraud Detector started (PID: $FRAUD_PID)${NC}" || \
    echo -e "${RED}   ❌ Fraud Detector failed - check logs/fraud_detector.log${NC}"

# Start Stock Monitor
echo -e "${YELLOW}   Starting Stock Monitor...${NC}"
nohup python3 stock_monitor.py > logs/stock_monitor.log 2>&1 &
STOCK_PID=$!
echo $STOCK_PID > logs/stock_monitor.pid
sleep 2
ps -p $STOCK_PID > /dev/null && \
    echo -e "${GREEN}   ✅ Stock Monitor started (PID: $STOCK_PID)${NC}" || \
    echo -e "${RED}   ❌ Stock Monitor failed - check logs/stock_monitor.log${NC}"

# Start Review Watcher
echo -e "${YELLOW}   Starting Review Watcher...${NC}"
nohup python3 review_watcher.py > logs/review_watcher.log 2>&1 &
REVIEW_PID=$!
echo $REVIEW_PID > logs/review_watcher.pid
sleep 2
ps -p $REVIEW_PID > /dev/null && \
    echo -e "${GREEN}   ✅ Review Watcher started (PID: $REVIEW_PID)${NC}" || \
    echo -e "${RED}   ❌ Review Watcher failed - check logs/review_watcher.log${NC}"

echo ""

# ============================================================
# STEP 6: Open Browser and Start Dashboard
# ============================================================
echo -e "${YELLOW}[5/6] Opening browser tabs...${NC}"
sleep 2
open "http://localhost:8080/shop" 2>/dev/null || true
sleep 1
open "http://localhost:8501" 2>/dev/null || true

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${GREEN}   ✅ ALL SERVICES STARTED SUCCESSFULLY!${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "${GREEN}   🛍️  Store:      http://localhost:8080/shop${NC}"
echo -e "${GREEN}   📊 Dashboard:  http://localhost:8501${NC}"
echo -e "${GREEN}   🔐 WP Admin:   http://localhost:8080/wp-admin${NC}"
echo ""
echo -e "${YELLOW}   📋 Test Cards:${NC}"
echo -e "${GREEN}   ✅ Approved:   4242 4242 4242 4242${NC}"
echo -e "${RED}   ❌ Declined:   4000 0000 0000 0002${NC}"
echo ""
echo -e "${YELLOW}   📁 Logs:${NC}"
echo -e "   watch_orders:    logs/watch_orders.log${NC}"
echo -e "   fraud_detector:  logs/fraud_detector.log${NC}"
echo -e "   stock_monitor:   logs/stock_monitor.log${NC}"
echo -e "   review_watcher:  logs/review_watcher.log${NC}"
echo ""
echo -e "${YELLOW}   🛑 To stop: ./stop_all.sh${NC}"
echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   [6/6] Starting Dashboard (Ctrl+C to stop)${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

streamlit run dashboard.py --server.port 8501