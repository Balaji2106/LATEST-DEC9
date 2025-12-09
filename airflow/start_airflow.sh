#!/bin/bash

# ============================================================================
# Airflow Start Script
# ============================================================================

set -e  # Exit on error

echo "==========================================="
echo "  Starting Apache Airflow"
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

# Set Airflow home
export AIRFLOW_HOME=~/airflow
echo "📁 Airflow home: $AIRFLOW_HOME"
echo ""

# Check if Airflow is installed
if ! command -v airflow &> /dev/null; then
    echo -e "${RED}❌ Airflow not found. Please run setup_airflow.sh first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Airflow installation found${NC}"
echo ""

# Check if database is initialized
if [ ! -f "$AIRFLOW_HOME/airflow.db" ]; then
    echo -e "${RED}❌ Airflow database not initialized. Please run setup_airflow.sh first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Airflow database found${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p "$AIRFLOW_HOME/logs"

# Kill any existing Airflow processes
echo "🔍 Checking for existing Airflow processes..."
WEBSERVER_PID=$(pgrep -f "airflow webserver" || echo "")
SCHEDULER_PID=$(pgrep -f "airflow scheduler" || echo "")

if [ ! -z "$WEBSERVER_PID" ]; then
    echo -e "${YELLOW}⚠️  Existing webserver found (PID: $WEBSERVER_PID). Stopping...${NC}"
    kill $WEBSERVER_PID 2>/dev/null || true
    sleep 2
fi

if [ ! -z "$SCHEDULER_PID" ]; then
    echo -e "${YELLOW}⚠️  Existing scheduler found (PID: $SCHEDULER_PID). Stopping...${NC}"
    kill $SCHEDULER_PID 2>/dev/null || true
    sleep 2
fi

echo -e "${GREEN}✅ No conflicting processes${NC}"
echo ""

# Start Airflow webserver in background
echo "🌐 Starting Airflow webserver on port 8080..."
nohup airflow webserver --port 8080 > "$AIRFLOW_HOME/logs/webserver.log" 2>&1 &
WEBSERVER_PID=$!
echo -e "${GREEN}✅ Webserver started (PID: $WEBSERVER_PID)${NC}"
echo ""

# Wait a moment for webserver to start
sleep 3

# Start Airflow scheduler in background
echo "📅 Starting Airflow scheduler..."
nohup airflow scheduler > "$AIRFLOW_HOME/logs/scheduler.log" 2>&1 &
SCHEDULER_PID=$!
echo -e "${GREEN}✅ Scheduler started (PID: $SCHEDULER_PID)${NC}"
echo ""

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if processes are still running
if ps -p $WEBSERVER_PID > /dev/null; then
    echo -e "${GREEN}✅ Webserver is running${NC}"
else
    echo -e "${RED}❌ Webserver failed to start. Check logs: $AIRFLOW_HOME/logs/webserver.log${NC}"
    exit 1
fi

if ps -p $SCHEDULER_PID > /dev/null; then
    echo -e "${GREEN}✅ Scheduler is running${NC}"
else
    echo -e "${RED}❌ Scheduler failed to start. Check logs: $AIRFLOW_HOME/logs/scheduler.log${NC}"
    exit 1
fi

echo ""
echo "==========================================="
echo "  ✅ Airflow Started Successfully!"
echo "==========================================="
echo ""
echo -e "${BLUE}📊 Access Airflow UI:${NC}"
echo "   URL: http://localhost:8080"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo -e "${BLUE}📝 Process IDs:${NC}"
echo "   Webserver PID: $WEBSERVER_PID"
echo "   Scheduler PID: $SCHEDULER_PID"
echo ""
echo -e "${BLUE}📋 Log Files:${NC}"
echo "   Webserver: $AIRFLOW_HOME/logs/webserver.log"
echo "   Scheduler: $AIRFLOW_HOME/logs/scheduler.log"
echo ""
echo -e "${BLUE}🛑 To stop Airflow:${NC}"
echo "   ./airflow/stop_airflow.sh"
echo "   OR manually: kill $WEBSERVER_PID $SCHEDULER_PID"
echo ""
echo -e "${BLUE}🔍 To view logs:${NC}"
echo "   tail -f $AIRFLOW_HOME/logs/webserver.log"
echo "   tail -f $AIRFLOW_HOME/logs/scheduler.log"
echo ""
echo -e "${BLUE}🧪 To test RCA integration:${NC}"
echo "   1. Enable 'test_rca_integration' DAG in UI"
echo "   2. Trigger: airflow dags trigger test_rca_integration"
echo "   3. Or test specific task:"
echo "      airflow tasks test test_rca_integration test_connection_error 2025-01-01"
echo ""
echo "==========================================="
echo ""
