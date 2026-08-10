#!/bin/bash

# ============================================================
# E-COMMERCE ANALYTICS - STOP ALL SERVICES
# ============================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}   🛑 STOPPING ALL SERVICES${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

PROJECT_DIR=~/ecommerce-project
cd $PROJECT_DIR

# Stop Order Watcher
pkill -f "watch_orders.py" 2>/dev/null
rm -f logs/watch_orders.pid
echo -e "${GREEN}   ✅ Order Watcher stopped${NC}"

# Stop Fraud Detector
pkill -f "fraud_detector_ml.py" 2>/dev/null
rm -f logs/fraud_detector.pid
echo -e "${GREEN}   ✅ Fraud Detector stopped${NC}"

# Stop Stock Monitor
pkill -f "stock_monitor.py" 2>/dev/null
rm -f logs/stock_monitor.pid
echo -e "${GREEN}   ✅ Stock Monitor stopped${NC}"

# Stop Review Watcher
pkill -f "review_watcher.py" 2>/dev/null
rm -f logs/review_watcher.pid
echo -e "${GREEN}   ✅ Review Watcher stopped${NC}"

# Stop Dashboard
pkill -f "streamlit" 2>/dev/null
echo -e "${GREEN}   ✅ Dashboard stopped${NC}"

# Stop Docker
echo -e "${YELLOW}   Stopping Docker services...${NC}"
docker-compose down
echo -e "${GREEN}   ✅ Docker services stopped${NC}"

echo ""
echo -e "${GREEN}   ✅ ALL SERVICES STOPPED!${NC}"
echo -e "${YELLOW}   To start again: ./start_all.sh${NC}"
echo ""
echo -e "${BLUE}============================================================${NC}"
echo ""