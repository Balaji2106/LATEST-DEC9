# AIOps RCA Assistant - Complete Project Documentation

## 📋 Table of Contents

This documentation provides a complete guide to the AIOps Root Cause Analysis (RCA) Assistant project. Start here and follow the documents in order for a complete understanding.

### Documentation Files

1. **[00_PROJECT_OVERVIEW.md](00_PROJECT_OVERVIEW.md)** (This file) - Project introduction and overview
2. **[01_ARCHITECTURE.md](01_ARCHITECTURE.md)** - System architecture and component design
3. **[02_AZURE_SETUP.md](02_AZURE_SETUP.md)** - Azure permissions, resources, and configuration
4. **[03_INSTALLATION.md](03_INSTALLATION.md)** - Step-by-step installation guide
5. **[04_CONFIGURATION.md](04_CONFIGURATION.md)** - Environment variables and settings
6. **[05_API_REFERENCE.md](05_API_REFERENCE.md)** - Complete API endpoint documentation
7. **[06_INTEGRATIONS.md](06_INTEGRATIONS.md)** - JIRA, Slack, Databricks, ADF, Airflow integrations
8. **[07_FUNCTION_REFERENCE.md](07_FUNCTION_REFERENCE.md)** - Function-by-function code reference
9. **[08_DEPLOYMENT.md](08_DEPLOYMENT.md)** - Production deployment guide
10. **[09_TROUBLESHOOTING.md](09_TROUBLESHOOTING.md)** - Common issues and solutions
11. **[10_DEVELOPER_GUIDE.md](10_DEVELOPER_GUIDE.md)** - Extending and customizing the system

---

## 🎯 Project Overview

### What is AIOps RCA Assistant?

The **AIOps Root Cause Analysis (RCA) Assistant** is an intelligent, automated incident management system that:

- **Automatically detects** failures from Azure Data Factory, Databricks, and Airflow
- **Analyzes errors** using AI (Google Gemini) to generate root cause analysis
- **Creates tickets** in JIRA with detailed RCA and recommendations
- **Sends notifications** to Slack with actionable insights
- **Tracks SLA** compliance and resolution time
- **Provides dashboards** for real-time incident monitoring
- **Enables auto-remediation** for known, fixable issues

### Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Source Monitoring** | ADF, Databricks, Airflow integration |
| **AI-Powered RCA** | Google Gemini generates intelligent root cause analysis |
| **Automated JIRA Ticketing** | Creates structured tickets with RCA, severity, priority |
| **Slack Integration** | Real-time notifications with bidirectional updates |
| **SLA Tracking** | Automatic SLA calculation based on priority |
| **Interactive Dashboard** | Web-based UI for ticket management |
| **Bidirectional Sync** | JIRA status updates sync back to RCA system |
| **Auto-Remediation** | Automatic fixes for known error patterns |
| **Audit Trail** | Complete history of all actions and state changes |
| **FinOps Tagging** | Cost center, team, owner tracking |

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                              │
├─────────────────────────────────────────────────────────────────┤
│  Azure Data Factory  │  Databricks  │  Airflow  │  Azure Monitor│
└────────┬─────────────┴──────┬───────┴────┬──────┴───────┬───────┘
         │                    │            │              │
         │ Webhooks          │ Alerts     │ Callbacks    │ Alerts
         ▼                    ▼            ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI RCA SYSTEM                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Webhook    │  │    Error     │  │  Duplicate   │          │
│  │  Receivers   │→ │Classification│→ │  Detection   │          │
│  └──────────────┘  └──────────────┘  └──────┬───────┘          │
│                                              ▼                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │          AI-Powered RCA Generation (Gemini)              │  │
│  │  • Root Cause Analysis  • Recommendations  • Severity    │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                              ▼                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   SQLite     │  │    JIRA      │  │    Slack     │          │
│  │   Ticket     │→ │   Ticket     │→ │  Notification│          │
│  │   Storage    │  │   Creation   │  │              │          │
│  └──────────────┘  └──────┬───────┘  └──────────────┘          │
└──────────────────────────┬┼────────────────────────────────────┘
                           ││
                           ││ Bidirectional Sync
                           ▼▼
        ┌────────────────────────────────────────┐
        │      Web Dashboard (HTML/JS)           │
        │  • Ticket Management                   │
        │  • Real-time Updates (WebSocket)       │
        │  • SLA Monitoring                      │
        │  • Audit Trail Viewer                  │
        └────────────────────────────────────────┘
```

---

## 🔑 Key Technologies

### Backend
- **FastAPI** - Modern Python web framework
- **Python 3.12** - Core programming language
- **SQLite** - Ticket and audit storage
- **SQLAlchemy** - Database ORM
- **Uvicorn** - ASGI server

### AI/ML
- **Google Gemini 2.5 Flash** - AI-powered RCA generation
- **Regex Pattern Matching** - Error classification

### Integrations
- **JIRA Cloud API** - Ticket management
- **Slack Webhooks** - Notifications
- **Azure Monitor** - Alert webhooks
- **Databricks API** - Cluster/job monitoring
- **Airflow API** - DAG/task failure callbacks

### Frontend
- **HTML5/CSS3/JavaScript** - Dashboard UI
- **WebSocket** - Real-time updates
- **Fetch API** - REST client

### Cloud & Storage
- **Azure Blob Storage** - Log/payload archival
- **Azure Key Vault** - Secrets management (optional)
- **Azure Monitor** - Alert rules

---

## 📊 System Capabilities

### Supported Failure Sources

| Source | Integration Method | Trigger |
|--------|-------------------|---------|
| **Azure Data Factory** | Azure Monitor Alert → Webhook | Pipeline/activity failures |
| **Databricks** | Azure Monitor Alert → Webhook | Cluster/job failures |
| **Airflow** | Task failure callback → POST | DAG task failures |
| **Azure Monitor** | Action Group → Webhook | Custom log queries |

### Auto-Remediable Error Types

The system can automatically remediate:

1. **Databricks Cluster Issues**
   - Cloud provider resource stockout
   - Driver unresponsive
   - Bootstrap timeout
   - Spot instance preemption

2. **Airflow Task Failures**
   - Connection errors (retry with backoff)
   - Timeout errors (extend timeout, retry)
   - Sensor timeouts (check upstream, retry)
   - API errors (retry with backoff)

3. **Network/Connectivity Issues**
   - Transient network failures
   - DNS resolution errors (retry)
   - Connection pool exhaustion

### Non-Remediable Errors (Require Manual Intervention)

- Authentication/permission errors
- Schema validation failures
- Data quality issues
- Application logic bugs
- Resource quota exceeded

---

## 🎓 Learning Path

### For New Users
1. Start with [01_ARCHITECTURE.md](01_ARCHITECTURE.md) to understand system design
2. Review [02_AZURE_SETUP.md](02_AZURE_SETUP.md) for Azure prerequisites
3. Follow [03_INSTALLATION.md](03_INSTALLATION.md) to set up locally
4. Read [04_CONFIGURATION.md](04_CONFIGURATION.md) to configure the system
5. Test with [06_INTEGRATIONS.md](06_INTEGRATIONS.md) examples

### For Developers
1. Understand architecture in [01_ARCHITECTURE.md](01_ARCHITECTURE.md)
2. Study function details in [07_FUNCTION_REFERENCE.md](07_FUNCTION_REFERENCE.md)
3. Review API endpoints in [05_API_REFERENCE.md](05_API_REFERENCE.md)
4. Follow [10_DEVELOPER_GUIDE.md](10_DEVELOPER_GUIDE.md) to extend functionality

### For DevOps/SRE
1. Review [02_AZURE_SETUP.md](02_AZURE_SETUP.md) for resource requirements
2. Follow [08_DEPLOYMENT.md](08_DEPLOYMENT.md) for production deployment
3. Keep [09_TROUBLESHOOTING.md](09_TROUBLESHOOTING.md) handy for issues

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Python 3.12+
- Git
- Azure subscription (for integrations)
- JIRA Cloud account
- Slack workspace

### Installation

```bash
# 1. Clone repository
git clone https://github.com/Balaji2106/LATEST-DEC9.git
cd LATEST-DEC9

# 2. Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
cd genai_rca_assistant
pip install -r requirements.txt

# 4. Set environment variables
export GEMINI_API_KEY="your-gemini-api-key"
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_EMAIL="your-email@company.com"
export JIRA_API_TOKEN="your-jira-token"
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"

# 5. Run the application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 6. Access dashboard
# Open browser: http://localhost:8000/dashboard
```

---

## 📈 Use Cases

### 1. Data Pipeline Monitoring
**Scenario:** Azure Data Factory pipeline fails due to missing source file

**Flow:**
1. ADF pipeline fails
2. Azure Monitor alert triggers
3. RCA system receives webhook
4. AI analyzes error: "Source file not found in ADLS Gen2"
5. JIRA ticket created with recommendations
6. Slack notification sent to #data-engineering
7. Engineer reviews, fixes upstream issue
8. Updates JIRA to Done
9. Ticket auto-closes in RCA system

### 2. Databricks Cluster Failures
**Scenario:** Databricks cluster fails due to cloud provider resource stockout

**Flow:**
1. Cluster fails to start
2. Azure Monitor detects failure
3. RCA system classifies as auto-remediable
4. Logic App triggered to retry with different instance type
5. If retry succeeds, ticket marked as auto-resolved
6. If retry fails, escalated to engineering team

### 3. Airflow DAG Monitoring
**Scenario:** Airflow task fails due to connection timeout

**Flow:**
1. Airflow task times out connecting to database
2. Failure callback sends to RCA system
3. Error classified as "ConnectionError" (remediable)
4. AI recommends: "Retry with exponential backoff"
5. JIRA ticket created
6. Airflow automatically retries per configuration
7. Success on retry 2
8. Ticket updated with resolution

---

## 🔒 Security Considerations

### Secrets Management
- **Never** commit API keys, tokens, or passwords to Git
- Use environment variables or Azure Key Vault
- Rotate credentials regularly

### Azure Permissions
- Follow principle of least privilege
- Use managed identities where possible
- Audit access logs regularly

### Network Security
- Use HTTPS for all external communications
- Implement webhook secret validation
- Restrict inbound traffic to known IPs

### Data Privacy
- Sanitize error messages before storing
- Redact sensitive data (credentials, PII)
- Encrypt data at rest (Azure Blob Storage)

---

## 📞 Support & Contribution

### Getting Help
- Review [09_TROUBLESHOOTING.md](09_TROUBLESHOOTING.md) for common issues
- Check GitHub Issues for known problems
- Contact the development team

### Contributing
- Follow [10_DEVELOPER_GUIDE.md](10_DEVELOPER_GUIDE.md) for development setup
- Submit pull requests with clear descriptions
- Include tests for new features
- Update documentation

---

## 📝 License & Acknowledgments

### Project Information
- **Project Name:** AIOps RCA Assistant
- **Version:** 1.0.0
- **Status:** Production Ready
- **Maintained By:** Data Engineering & DevOps Team

### Technologies Used
- FastAPI - https://fastapi.tiangolo.com/
- Google Gemini AI - https://ai.google.dev/
- JIRA Cloud API - https://developer.atlassian.com/cloud/jira/
- Slack API - https://api.slack.com/
- Azure Services - https://azure.microsoft.com/

---

## 🗺️ Roadmap

### Completed ✅
- Multi-source failure detection (ADF, Databricks, Airflow)
- AI-powered RCA generation
- JIRA integration with bidirectional sync
- Slack notifications
- Web dashboard with real-time updates
- Auto-remediation for Databricks
- SLA tracking
- Audit trail

### In Progress 🚧
- Enhanced auto-remediation for Airflow
- ML-based failure prediction
- Anomaly detection
- Custom alert rule builder

### Planned 📋
- Microsoft Teams integration
- ServiceNow integration
- Grafana dashboard integration
- Mobile app
- Advanced analytics and reporting
- Auto-scaling remediation workers

---

## 📚 Next Steps

1. **Understand the Architecture** → Read [01_ARCHITECTURE.md](01_ARCHITECTURE.md)
2. **Set Up Azure Resources** → Follow [02_AZURE_SETUP.md](02_AZURE_SETUP.md)
3. **Install Locally** → Complete [03_INSTALLATION.md](03_INSTALLATION.md)
4. **Configure Services** → Review [04_CONFIGURATION.md](04_CONFIGURATION.md)
5. **Test Integrations** → Try examples in [06_INTEGRATIONS.md](06_INTEGRATIONS.md)

---

**Happy Incident Resolution! 🚀**

*Last Updated: December 11, 2025*
