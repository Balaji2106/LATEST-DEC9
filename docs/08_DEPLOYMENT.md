# Deployment Guide

Complete guide for deploying the AIOps RCA Assistant to production environments.

---

## 📋 Table of Contents

1. [Deployment Options](#deployment-options)
2. [Azure App Service Deployment](#azure-app-service-deployment)
3. [Azure Container Instances](#azure-container-instances)
4. [Azure Kubernetes Service (AKS)](#azure-kubernetes-service-aks)
5. [VM Deployment](#vm-deployment)
6. [Production Checklist](#production-checklist)
7. [Monitoring & Observability](#monitoring--observability)
8. [Scaling Considerations](#scaling-considerations)

---

## Deployment Options

| Option | Best For | Complexity | Cost | Scalability |
|--------|----------|------------|------|-------------|
| **Azure App Service** | Quick production deployment | Low | $ | Medium |
| **Azure Container Instances** | Lightweight containerized deployment | Low | $ | Low |
| **Azure Kubernetes Service** | Enterprise, high availability | High | $$$ | Very High |
| **Virtual Machine** | Full control, custom setup | Medium | $$ | Medium |

---

## Azure App Service Deployment

### Prerequisites

- Azure subscription
- Azure CLI installed
- Git repository

### Step 1: Create App Service

```bash
# Create resource group
az group create \
  --name rg-aiops-rca-prod \
  --location eastus

# Create App Service plan (Linux)
az appservice plan create \
  --name plan-aiops-rca \
  --resource-group rg-aiops-rca-prod \
  --sku B2 \
  --is-linux

# Create web app
az webapp create \
  --name aiops-rca-prod \
  --resource-group rg-aiops-rca-prod \
  --plan plan-aiops-rca \
  --runtime "PYTHON:3.12"
```

### Step 2: Configure Application Settings

```bash
# Set Python version
az webapp config set \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --linux-fx-version "PYTHON|3.12"

# Configure startup command
az webapp config set \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --startup-file "startup.sh"
```

### Step 3: Create startup.sh

**File:** `genai_rca_assistant/startup.sh`

```bash
#!/bin/bash
cd /home/site/wwwroot/genai_rca_assistant
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

```bash
chmod +x genai_rca_assistant/startup.sh
```

### Step 4: Configure Environment Variables

```bash
# Set environment variables (use Azure Key Vault for production)
az webapp config appsettings set \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --settings \
    PUBLIC_BASE_URL="https://aiops-rca-prod.azurewebsites.net" \
    AI_PROVIDER="gemini" \
    GEMINI_API_KEY="@Microsoft.KeyVault(SecretUri=https://kv-aiops.vault.azure.net/secrets/gemini-api-key/)" \
    DB_TYPE="azuresql" \
    AZURE_SQL_SERVER="aiops-sql-prod.database.windows.net" \
    AZURE_SQL_DATABASE="aiops_rca" \
    AZURE_SQL_USERNAME="sqladmin" \
    AZURE_SQL_PASSWORD="@Microsoft.KeyVault(SecretUri=https://kv-aiops.vault.azure.net/secrets/sql-password/)" \
    ITSM_TOOL="jira" \
    JIRA_DOMAIN="https://your-company.atlassian.net" \
    JIRA_USER_EMAIL="aiops-bot@company.com" \
    JIRA_API_TOKEN="@Microsoft.KeyVault(SecretUri=https://kv-aiops.vault.azure.net/secrets/jira-token/)" \
    JIRA_PROJECT_KEY="APAIOPS" \
    SLACK_BOT_TOKEN="@Microsoft.KeyVault(SecretUri=https://kv-aiops.vault.azure.net/secrets/slack-token/)" \
    SLACK_ALERT_CHANNEL="C01234567" \
    AZURE_BLOB_ENABLED="true" \
    AZURE_STORAGE_CONN="@Microsoft.KeyVault(SecretUri=https://kv-aiops.vault.azure.net/secrets/storage-conn/)"
```

### Step 5: Enable System-Assigned Managed Identity

```bash
# Enable managed identity
az webapp identity assign \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod

# Grant Key Vault access
IDENTITY_ID=$(az webapp identity show \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --query principalId -o tsv)

az keyvault set-policy \
  --name kv-aiops \
  --object-id $IDENTITY_ID \
  --secret-permissions get list
```

### Step 6: Deploy Code

**Option A: Git Deployment**

```bash
# Configure git deployment
az webapp deployment source config \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --repo-url https://github.com/Balaji2106/LATEST-DEC9.git \
  --branch main \
  --manual-integration

# Or enable continuous deployment
az webapp deployment source config \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --repo-url https://github.com/Balaji2106/LATEST-DEC9.git \
  --branch main
```

**Option B: ZIP Deployment**

```bash
# Create deployment package
cd genai_rca_assistant
zip -r ../rca-app.zip .

# Deploy
az webapp deployment source config-zip \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --src ../rca-app.zip
```

### Step 7: Configure Custom Domain & SSL

```bash
# Add custom domain
az webapp config hostname add \
  --resource-group rg-aiops-rca-prod \
  --webapp-name aiops-rca-prod \
  --hostname aiops-rca.company.com

# Enable HTTPS
az webapp update \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --https-only true

# Bind SSL certificate (managed certificate)
az webapp config ssl create \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --hostname aiops-rca.company.com
```

### Step 8: Verify Deployment

```bash
# Check application logs
az webapp log tail \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod

# Test endpoint
curl https://aiops-rca-prod.azurewebsites.net/api/summary
```

---

## Azure Container Instances

### Step 1: Create Dockerfile

**File:** `genai_rca_assistant/Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft ODBC Driver (for Azure SQL)
RUN apt-get update && apt-get install -y curl gnupg \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directory
RUN mkdir -p data

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 2: Build and Push to Azure Container Registry

```bash
# Create ACR
az acr create \
  --resource-group rg-aiops-rca-prod \
  --name acraiopsprod \
  --sku Basic

# Build image in ACR
az acr build \
  --registry acraiopsprod \
  --image aiops-rca:v1.0 \
  --file Dockerfile \
  .
```

### Step 3: Deploy to ACI

```bash
# Create container instance
az container create \
  --resource-group rg-aiops-rca-prod \
  --name aci-aiops-rca \
  --image acraiopsprod.azurecr.io/aiops-rca:v1.0 \
  --cpu 2 \
  --memory 4 \
  --registry-login-server acraiopsprod.azurecr.io \
  --registry-username $(az acr credential show --name acraiopsprod --query username -o tsv) \
  --registry-password $(az acr credential show --name acraiopsprod --query passwords[0].value -o tsv) \
  --dns-name-label aiops-rca-prod \
  --ports 8000 \
  --environment-variables \
    PUBLIC_BASE_URL="http://aiops-rca-prod.eastus.azurecontainer.io:8000" \
    AI_PROVIDER="gemini"
```

---

## Azure Kubernetes Service (AKS)

### Step 1: Create AKS Cluster

```bash
# Create AKS cluster
az aks create \
  --resource-group rg-aiops-rca-prod \
  --name aks-aiops-rca \
  --node-count 2 \
  --node-vm-size Standard_D2s_v3 \
  --enable-managed-identity \
  --attach-acr acraiopsprod \
  --generate-ssh-keys

# Get credentials
az aks get-credentials \
  --resource-group rg-aiops-rca-prod \
  --name aks-aiops-rca
```

### Step 2: Create Kubernetes Manifests

**File:** `k8s/deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aiops-rca
  labels:
    app: aiops-rca
spec:
  replicas: 3
  selector:
    matchLabels:
      app: aiops-rca
  template:
    metadata:
      labels:
        app: aiops-rca
    spec:
      containers:
      - name: aiops-rca
        image: acraiopsprod.azurecr.io/aiops-rca:v1.0
        ports:
        - containerPort: 8000
        env:
        - name: PUBLIC_BASE_URL
          value: "https://aiops-rca.company.com"
        - name: AI_PROVIDER
          value: "gemini"
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: gemini-api-key
        - name: DB_TYPE
          value: "azuresql"
        - name: AZURE_SQL_SERVER
          value: "aiops-sql-prod.database.windows.net"
        - name: AZURE_SQL_DATABASE
          value: "aiops_rca"
        - name: AZURE_SQL_USERNAME
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: sql-username
        - name: AZURE_SQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: aiops-secrets
              key: sql-password
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/summary
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

**File:** `k8s/service.yaml`

```yaml
apiVersion: v1
kind: Service
metadata:
  name: aiops-rca-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: aiops-rca
```

### Step 3: Create Secrets

```bash
# Create Kubernetes secrets
kubectl create secret generic aiops-secrets \
  --from-literal=gemini-api-key='your-gemini-key' \
  --from-literal=sql-username='sqladmin' \
  --from-literal=sql-password='your-sql-password' \
  --from-literal=jira-token='your-jira-token' \
  --from-literal=slack-token='your-slack-token'
```

### Step 4: Deploy

```bash
# Apply manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Verify deployment
kubectl get pods
kubectl get services

# Get external IP
kubectl get service aiops-rca-service
```

---

## VM Deployment

### Step 1: Create VM

```bash
# Create Ubuntu VM
az vm create \
  --resource-group rg-aiops-rca-prod \
  --name vm-aiops-rca \
  --image Ubuntu2204 \
  --size Standard_D2s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard

# Open port 8000
az vm open-port \
  --resource-group rg-aiops-rca-prod \
  --name vm-aiops-rca \
  --port 8000
```

### Step 2: SSH and Install Dependencies

```bash
# SSH to VM
ssh azureuser@<VM_PUBLIC_IP>

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.12
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev

# Install ODBC driver
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

### Step 3: Deploy Application

```bash
# Clone repository
git clone https://github.com/Balaji2106/LATEST-DEC9.git
cd LATEST-DEC9/genai_rca_assistant

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
nano .env
# (Paste production configuration)

# Test run
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 4: Configure systemd Service

**File:** `/etc/systemd/system/aiops-rca.service`

```ini
[Unit]
Description=AIOps RCA Assistant
After=network.target

[Service]
Type=simple
User=azureuser
WorkingDirectory=/home/azureuser/LATEST-DEC9/genai_rca_assistant
Environment="PATH=/home/azureuser/LATEST-DEC9/genai_rca_assistant/venv/bin"
ExecStart=/home/azureuser/LATEST-DEC9/genai_rca_assistant/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable aiops-rca
sudo systemctl start aiops-rca

# Check status
sudo systemctl status aiops-rca

# View logs
sudo journalctl -u aiops-rca -f
```

---

## Production Checklist

### Security

- [ ] HTTPS enabled with valid SSL certificate
- [ ] Secrets stored in Azure Key Vault
- [ ] Managed Identity enabled
- [ ] Network Security Groups configured
- [ ] API authentication enabled
- [ ] CORS configured properly
- [ ] Rate limiting implemented

### Database

- [ ] Azure SQL Server configured
- [ ] Connection pooling enabled
- [ ] Backups configured (automated daily backups)
- [ ] High availability enabled (if needed)

### Monitoring

- [ ] Application Insights enabled
- [ ] Log Analytics workspace configured
- [ ] Alerts configured for errors
- [ ] Health check endpoint monitored
- [ ] Performance metrics tracked

### High Availability

- [ ] Multiple instances/replicas
- [ ] Load balancer configured
- [ ] Auto-scaling rules set
- [ ] Disaster recovery plan documented

### Testing

- [ ] Integration tests passed
- [ ] End-to-end test completed
- [ ] Load testing performed
- [ ] Failover testing done

---

## Monitoring & Observability

### Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app aiops-rca-insights \
  --location eastus \
  --resource-group rg-aiops-rca-prod \
  --application-type web

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app aiops-rca-insights \
  --resource-group rg-aiops-rca-prod \
  --query instrumentationKey -o tsv)

# Configure in app
az webapp config appsettings set \
  --resource-group rg-aiops-rca-prod \
  --name aiops-rca-prod \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$INSTRUMENTATION_KEY
```

### Health Check Endpoint

Already available at `GET /api/summary`

### Alerts

```bash
# Create alert for errors
az monitor metrics alert create \
  --name "aiops-rca-error-alert" \
  --resource-group rg-aiops-rca-prod \
  --scopes /subscriptions/SUB_ID/resourceGroups/rg-aiops-rca-prod/providers/Microsoft.Web/sites/aiops-rca-prod \
  --condition "count customMetrics/errors > 10" \
  --description "Alert when error count exceeds 10"
```

---

## Scaling Considerations

### Horizontal Scaling

**App Service:**
```bash
# Scale out to 3 instances
az appservice plan update \
  --name plan-aiops-rca \
  --resource-group rg-aiops-rca-prod \
  --number-of-workers 3
```

**AKS:**
```bash
# Scale deployment
kubectl scale deployment aiops-rca --replicas=5
```

### Auto-Scaling

**App Service:**
```bash
# Configure auto-scaling (scale between 2-10 instances)
az monitor autoscale create \
  --resource-group rg-aiops-rca-prod \
  --name autoscale-aiops \
  --resource /subscriptions/SUB_ID/resourceGroups/rg-aiops-rca-prod/providers/Microsoft.Web/serverFarms/plan-aiops-rca \
  --min-count 2 \
  --max-count 10 \
  --count 2

# Add CPU-based scaling rule
az monitor autoscale rule create \
  --resource-group rg-aiops-rca-prod \
  --autoscale-name autoscale-aiops \
  --scale out 1 \
  --condition "Percentage CPU > 70 avg 5m"
```

---

**Next:** [09_TROUBLESHOOTING.md](09_TROUBLESHOOTING.md) - Troubleshooting Guide
