# AIOps RCA Assistant with Auto-Remediation

Enterprise-grade AI-powered Root Cause Analysis (RCA) and Auto-Remediation platform for Azure Data Factory, Databricks, and Apache Airflow pipelines.

## 🚀 Features

- **AI-Powered RCA**: Automated root cause analysis using Gemini/Ollama LLMs
- **Auto-Remediation**: Intelligent automatic remediation for common failures
- **Multi-Platform Support**: ADF, Databricks, and Airflow integration
- **JIRA Integration**: Automatic ticket creation and bidirectional sync
- **Slack Notifications**: Real-time alerts with actionable insights
- **Interactive Dashboard**: Web-based UI for ticket management
- **Logic Apps Integration**: Azure Logic Apps for automated remediation workflows
- **Cluster Failure Detection**: Advanced Databricks cluster error analysis

## 📁 Project Structure

```
.
├── genai_rca_assistant/           # Main RCA application
│   ├── main.py                    # FastAPI application & API endpoints
│   ├── dashboard.html             # Interactive dashboard UI
│   ├── login.html                 # User authentication page
│   ├── register.html              # User registration page
│   ├── databricks_api_utils.py    # Databricks API integration
│   ├── cluster_failure_detector.py # Cluster error detection logic
│   ├── airflow_integration.py     # Airflow RCA integration
│   ├── error_extractors.py        # Error pattern extractors
│   ├── gemini_test.py             # Gemini API testing utility
│   ├── requirements.txt           # Python dependencies
│   └── data/                      # Runtime data (gitignored)
│       └── tickets.db             # SQLite database for tickets
│
├── logic-apps/                    # Azure Logic Apps workflows
│   ├── playbook-retry-databricks-job.json
│   ├── playbook-retry-adf-pipeline.json
│   ├── playbook-restart-databricks-cluster.json
│   ├── playbook-reinstall-databricks-libraries.json
│   ├── playbook-retry-airflow-task.json
│   └── README.md                  # Logic Apps deployment guide
│
├── airflow/                       # Apache Airflow setup
│   ├── dags/                      # Airflow DAG definitions
│   │   ├── example_production_dag.py
│   │   ├── prod_etl_failure_test.py
│   │   ├── rca_callbacks.py
│   │   └── test_rca_integration_dag.py
│   ├── setup_airflow.sh           # Airflow installation script
│   ├── start_airflow.sh           # Start Airflow services
│   ├── stop_airflow.sh            # Stop Airflow services
│   ├── AIRFLOW_SETUP_GUIDE.md     # Airflow setup instructions
│   └── airflow/                   # Airflow runtime (gitignored)
│       ├── airflow.cfg
│       ├── airflow.db
│       ├── logs/
│       └── webserver_config.py
│
├── docs/                          # Documentation
│   ├── AI_DRIVEN_REMEDIATION_ARCHITECTURE.md
│   ├── AUTO_REMEDIATION_IMPLEMENTATION.md
│   ├── AUTO_REMEDIATION_SUMMARY.md
│   ├── AZURE_MONITOR_CLUSTER_ALERTS_SETUP.md
│   ├── AIRFLOW_INTEGRATION_SETUP.md
│   ├── COMPLETE_AUTO_REMEDIATION_DEPLOYMENT.md
│   ├── CONTINUOUS_MONITORING_FLOW.md
│   ├── PROJECT_STRUCTURE.md
│   └── TESTING_AUTO_REMEDIATION.md
│
├── test_auto_remediation.py       # Auto-remediation test suite
├── test_cluster_detection_coverage.py  # Cluster detection tests
├── .gitignore                     # Git ignore patterns
└── README.md                      # This file
```

## 🛠️ Quick Start

### Prerequisites

- Python 3.9+
- Azure subscription (for Logic Apps)
- Databricks workspace (optional)
- Apache Airflow 2.x (optional)
- Gemini API key or Ollama instance

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd LATEST-DEC9
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv aiops-proj-env
   source aiops-proj-env/bin/activate  # On Windows: aiops-proj-env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   cd genai_rca_assistant
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in `genai_rca_assistant/`:
   ```bash
   # AI Provider
   AI_PROVIDER=gemini  # or ollama
   GEMINI_API_KEY=your_gemini_api_key
   MODEL_ID=models/gemini-2.5-flash

   # Slack
   SLACK_BOT_TOKEN=xoxb-your-slack-token
   SLACK_ALERT_CHANNEL=aiops-rca-alerts

   # JIRA (optional)
   JIRA_URL=https://your-domain.atlassian.net
   JIRA_EMAIL=your-email@domain.com
   JIRA_API_TOKEN=your-jira-token
   JIRA_PROJECT_KEY=PROJ

   # Databricks (optional)
   DATABRICKS_HOST=https://adb-xxx.azuredatabricks.net
   DATABRICKS_TOKEN=dapi-xxx

   # Auto-Remediation
   AUTO_REMEDIATION_ENABLED=true
   LOGIC_APP_WEBHOOK_URL=https://your-logic-app-url
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

   Access the dashboard at: `http://localhost:8000/dashboard`

## 📚 Documentation

- **[Architecture Overview](docs/AI_DRIVEN_REMEDIATION_ARCHITECTURE.md)** - System architecture and design
- **[Auto-Remediation Implementation](docs/AUTO_REMEDIATION_IMPLEMENTATION.md)** - How auto-remediation works
- **[Azure Monitor Setup](docs/AZURE_MONITOR_CLUSTER_ALERTS_SETUP.md)** - Configure Azure Monitor alerts
- **[Airflow Integration](docs/AIRFLOW_INTEGRATION_SETUP.md)** - Set up Airflow monitoring
- **[Logic Apps Guide](logic-apps/README.md)** - Deploy Azure Logic Apps workflows
- **[Testing Guide](docs/TESTING_AUTO_REMEDIATION.md)** - Test auto-remediation features

## 🔧 Configuration

### Auto-Remediation Policies

Auto-remediation is triggered based on error types and confidence levels:

- **High Confidence (>80%)**: Automatic remediation
- **Medium Confidence (60-80%)**: Manual approval required
- **Low Confidence (<60%)**: Manual intervention only

Supported remediations:
- ✅ Retry failed pipelines
- ✅ Restart Databricks clusters
- ✅ Reinstall missing libraries
- ✅ Increase cluster resources
- ✅ Retry Airflow tasks

### JIRA Integration

Bidirectional sync between RCA system and JIRA:
- Automatic ticket creation on failure
- Status updates propagate both ways
- Comments and updates synchronized

### Slack Notifications

Real-time alerts with:
- Root cause analysis
- Confidence scores
- Recommended actions
- JIRA ticket links
- Dashboard quick links

## 🧪 Testing

Run auto-remediation tests:
```bash
python test_auto_remediation.py
```

Run cluster detection tests:
```bash
python test_cluster_detection_coverage.py
```

## 🚀 Deployment

### Deploy to Azure App Service

```bash
# Create App Service
az webapp create --name aiops-rca --resource-group myResourceGroup --runtime "PYTHON:3.9"

# Configure environment variables
az webapp config appsettings set --name aiops-rca --resource-group myResourceGroup --settings \
  GEMINI_API_KEY="your-key" \
  SLACK_BOT_TOKEN="your-token"

# Deploy
az webapp up --name aiops-rca
```

### Deploy Logic Apps

See [Logic Apps README](logic-apps/README.md) for detailed deployment instructions.

### Set up Airflow

See [Airflow Setup Guide](airflow/AIRFLOW_SETUP_GUIDE.md) for Airflow installation and configuration.

## 🔐 Security Best Practices

1. **Never commit secrets** - Use environment variables or Azure Key Vault
2. **Rotate tokens regularly** - Set 90-day expiration for Databricks PATs
3. **Use HTTPS** - Always use secure connections
4. **Enable authentication** - Protect all endpoints with JWT tokens
5. **Monitor access logs** - Track API usage in Databricks audit logs

## 📊 Monitoring

- **Dashboard**: Real-time ticket status at `/dashboard`
- **Audit Trail**: Complete action history
- **SLA Tracking**: Monitor MTTR and resolution times
- **Logic Apps**: View workflow runs in Azure Portal

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🆘 Support

For issues and questions:
1. Check the [documentation](docs/)
2. Review [testing guide](docs/TESTING_AUTO_REMEDIATION.md)
3. Check Logic App run history in Azure Portal
4. Review application logs

## 🎯 Roadmap

- [ ] Support for more data platforms (Synapse, Data Factory Gen2)
- [ ] Advanced ML-based failure prediction
- [ ] Cost optimization recommendations
- [ ] Multi-tenancy support
- [ ] Enhanced dashboard with real-time metrics

---

**Built with ❤️ for DataOps and MLOps teams**
