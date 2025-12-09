#!/bin/bash

# ============================================================================
# Airflow Installation Script with RCA Integration
# ============================================================================

set -e  # Exit on error

echo "=========================================="
echo "  Apache Airflow Setup with RCA"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "📋 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}❌ Python 3.8+ required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Python $PYTHON_VERSION${NC}"
echo ""

# Set Airflow home
export AIRFLOW_HOME=~/airflow
echo "📁 Airflow home: $AIRFLOW_HOME"
echo ""

# Create Airflow directory
mkdir -p $AIRFLOW_HOME
echo -e "${GREEN}✅ Created Airflow directory${NC}"
echo ""

# Install Airflow
echo "📦 Installing Apache Airflow 2.8.0..."
AIRFLOW_VERSION=2.8.0
PYTHON_VERSION_SHORT="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION_SHORT}.txt"

echo "Using constraints: $CONSTRAINT_URL"
echo ""

pip3 install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}" --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Airflow installed successfully${NC}"
else
    echo -e "${RED}❌ Airflow installation failed${NC}"
    exit 1
fi
echo ""

# Install additional packages
echo "📦 Installing additional packages..."
pip3 install requests pandas --quiet
pip3 install apache-airflow-providers-http --quiet
echo -e "${GREEN}✅ Additional packages installed${NC}"
echo ""

# Initialize Airflow database
echo "🗄️  Initializing Airflow database..."
airflow db init
echo -e "${GREEN}✅ Database initialized${NC}"
echo ""

# Create admin user
echo "👤 Creating admin user..."
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin 2>/dev/null || echo "User already exists"

echo -e "${GREEN}✅ Admin user created (username: admin, password: admin)${NC}"
echo ""

# Link DAGs directory
echo "🔗 Setting up DAGs directory..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DAG_SOURCE_DIR="$SCRIPT_DIR/dags"

if [ -d "$DAG_SOURCE_DIR" ]; then
    # Remove existing dags folder if it's a symlink
    if [ -L "$AIRFLOW_HOME/dags" ]; then
        rm "$AIRFLOW_HOME/dags"
    fi

    # Create symlink
    ln -sf "$DAG_SOURCE_DIR" "$AIRFLOW_HOME/dags"
    echo -e "${GREEN}✅ DAGs directory linked: $DAG_SOURCE_DIR${NC}"
else
    echo -e "${YELLOW}⚠️  DAGs directory not found: $DAG_SOURCE_DIR${NC}"
    echo "   Creating empty dags directory..."
    mkdir -p "$AIRFLOW_HOME/dags"
fi
echo ""

# Update airflow.cfg
echo "⚙️  Updating Airflow configuration..."
sed -i.bak 's/load_examples = True/load_examples = False/' "$AIRFLOW_HOME/airflow.cfg"
echo -e "${GREEN}✅ Configuration updated (load_examples = False)${NC}"
echo ""

# Summary
echo "=========================================="
echo "  ✅ Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure RCA webhook URL:"
echo "   Edit: $AIRFLOW_HOME/dags/rca_callbacks.py"
echo "   Update: RCA_WEBHOOK_URL and AIRFLOW_BASE_URL"
echo ""
echo "2. Start Airflow:"
echo "   ./airflow/start_airflow.sh"
echo ""
echo "3. Access Airflow UI:"
echo "   URL: http://localhost:8080"
echo "   Username: admin"
echo "   Password: admin"
echo ""
echo "4. Test RCA integration:"
echo "   airflow tasks test test_rca_integration test_connection_error 2025-01-01"
echo ""
echo "=========================================="
echo ""
