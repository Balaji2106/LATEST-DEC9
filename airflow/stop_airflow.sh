#!/bin/bash

# ============================================================================
# Airflow Stop Script
# ============================================================================

echo "==========================================="
echo "  Stopping Apache Airflow"
echo "==========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find Airflow processes
WEBSERVER_PIDS=$(pgrep -f "airflow webserver" || echo "")
SCHEDULER_PIDS=$(pgrep -f "airflow scheduler" || echo "")

# Stop webserver
if [ ! -z "$WEBSERVER_PIDS" ]; then
    echo "🛑 Stopping Airflow webserver..."
    echo "   PIDs: $WEBSERVER_PIDS"
    for PID in $WEBSERVER_PIDS; do
        kill $PID 2>/dev/null || true
    done
    echo -e "${GREEN}✅ Webserver stopped${NC}"
else
    echo -e "${YELLOW}⚠️  No webserver process found${NC}"
fi

echo ""

# Stop scheduler
if [ ! -z "$SCHEDULER_PIDS" ]; then
    echo "🛑 Stopping Airflow scheduler..."
    echo "   PIDs: $SCHEDULER_PIDS"
    for PID in $SCHEDULER_PIDS; do
        kill $PID 2>/dev/null || true
    done
    echo -e "${GREEN}✅ Scheduler stopped${NC}"
else
    echo -e "${YELLOW}⚠️  No scheduler process found${NC}"
fi

echo ""

# Wait for processes to terminate
echo "⏳ Waiting for processes to terminate..."
sleep 3

# Check if any Airflow processes are still running
REMAINING=$(pgrep -f "airflow" || echo "")
if [ ! -z "$REMAINING" ]; then
    echo -e "${YELLOW}⚠️  Some Airflow processes still running (PIDs: $REMAINING)${NC}"
    echo "   Force killing remaining processes..."
    for PID in $REMAINING; do
        kill -9 $PID 2>/dev/null || true
    done
    sleep 1
fi

# Final check
STILL_RUNNING=$(pgrep -f "airflow" || echo "")
if [ -z "$STILL_RUNNING" ]; then
    echo -e "${GREEN}✅ All Airflow processes stopped${NC}"
else
    echo -e "${RED}❌ Some processes could not be stopped: $STILL_RUNNING${NC}"
    echo "   You may need to manually kill them: kill -9 $STILL_RUNNING"
    exit 1
fi

echo ""
echo "==========================================="
echo "  ✅ Airflow Stopped Successfully!"
echo "==========================================="
echo ""
echo "To start again: ./airflow/start_airflow.sh"
echo ""
