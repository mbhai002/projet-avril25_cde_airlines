# DST Airlines Documentation Package

## Quick Access Links

**Live System URLs:**
- **Dashboard:** http://35.181.7.121:8050
- **API Documentation:** http://35.181.7.121:8000/docs
- **Database Admin (pgAdmin):** http://35.181.7.121:5050

**EC2 Instance:**
- **IP Address:** 35.181.7.121
- **SSH:** `ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121`

---

## Documentation Files

This package contains three comprehensive documentation files:

### 1. AWS_DEPLOYMENT_CONFIGURATION.md
**Purpose:** Complete technical configuration and deployment guide

**Contents:**
- AWS infrastructure setup details
- EC2 instance configuration
- Security group rules
- Docker installation steps
- Environment variables reference
- Database configuration
- Troubleshooting guide
- Backup and maintenance procedures
- Security best practices
- Cost optimization tips

**Target Audience:** System administrators, DevOps engineers, technical team members

**Key Sections:**
- Infrastructure details and specifications
- Step-by-step configuration instructions
- Docker Compose commands reference
- Database credentials and connection strings
- Makefile commands
- Common issues and solutions

---

### 2. USER_GUIDE.md
**Purpose:** End-user manual for using the application

**Contents:**
- System overview and capabilities
- Dashboard navigation guide
- API usage documentation
- Database management instructions
- Data collection process explanation
- Machine learning predictions guide
- Common tasks and workflows
- FAQ section

**Target Audience:** End users, analysts, data scientists, project stakeholders

**Key Sections:**
- How to access and navigate the dashboard
- Understanding flight predictions
- Using the REST API
- Interpreting analytics and statistics
- Searching and filtering flights
- Weather data visualization
- ML model performance metrics

---

### 3. README.md
**Purpose:** Quick start guide (already existed)

**Contents:**
- Project description
- Basic Docker commands
- Quick setup instructions

---

## Converting to PDF

### Option 1: Using Online Converter (Easiest)
1. Go to https://www.markdowntopdf.com/ or https://md2pdf.netlify.app/
2. Upload `AWS_DEPLOYMENT_CONFIGURATION.md`
3. Download the PDF
4. Repeat for `USER_GUIDE.md`

### Option 2: Using Pandoc (Best Quality)

**Install Pandoc:**
```bash
# Windows (using Chocolatey)
choco install pandoc

# Or download from: https://pandoc.org/installing.html
```

**Convert to PDF:**
```bash
# Navigate to project directory
cd "C:\Users\mabha\Desktop\projet-avril25_cde_airlines-dockerisation"

# Convert deployment guide
pandoc AWS_DEPLOYMENT_CONFIGURATION.md -o AWS_DEPLOYMENT_CONFIGURATION.pdf --pdf-engine=wkhtmltopdf

# Convert user guide
pandoc USER_GUIDE.md -o USER_GUIDE.pdf --pdf-engine=wkhtmltopdf
```

### Option 3: Using VS Code Extension

1. Install "Markdown PDF" extension in VS Code
2. Open `AWS_DEPLOYMENT_CONFIGURATION.md`
3. Right-click → "Markdown PDF: Export (pdf)"
4. Repeat for `USER_GUIDE.md`

### Option 4: Using Chrome/Edge Browser

1. Open markdown file in VS Code or any markdown viewer
2. Use browser's print function (Ctrl+P)
3. Select "Save as PDF"
4. Adjust margins and settings
5. Save

---

## Documentation Structure Summary

### AWS_DEPLOYMENT_CONFIGURATION.md
```
├── AWS Infrastructure Setup
├── EC2 Instance Configuration
├── Security Group Rules
├── Docker Installation
├── Application Configuration
├── Environment Variables
├── Database Setup
├── Docker Services
└── Troubleshooting
```

### USER_GUIDE.md
```
├── System Overview
├── Accessing the Application
├── Dashboard Guide
│   ├── Vols (Flights)
│   ├── Meteo (Weather)
│   └── Analyses (Analytics)
├── API Documentation
│   ├── Endpoints Reference
│   └── Usage Examples
├── Database Management
├── Data Collection Process
├── Machine Learning Predictions
├── Common Tasks
└── FAQ
```

---

## Quick Start for New Users

### For Technical Team (Setup/Maintenance):
1. Read: `AWS_DEPLOYMENT_CONFIGURATION.md`
2. Follow deployment steps
3. Configure environment variables
4. Monitor system health

### For End Users (Using the System):
1. Read: `USER_GUIDE.md`
2. Access dashboard: http://35.181.7.121:8050
3. Explore the three main pages (Vols, Meteo, Analyses)
4. Use API for programmatic access

### For Data Scientists:
1. Read: `USER_GUIDE.md` (API and ML sections)
2. Access API docs: http://35.181.7.121:8000/docs
3. Connect to database via pgAdmin
4. Export data for analysis

---

## System Status Check

**Verify all services are running:**
```bash
ssh -i ~/Downloads/airlines-key-v2.pem ubuntu@35.181.7.121
cd projet-avril25_cde_airlines-dockerisation
docker-compose ps
```

**Expected Output:**
```
NAME                  STATUS
airlines_app          Up
airlines_dash         Up
airlines_fastapi      Up
airlines_mongodb      Up (healthy)
airlines_pgadmin      Up
airlines_postgresql   Up (healthy)
```

---

## Important Credentials

**EC2 SSH:**
- Key File: `airlines-key-v2.pem` (in Downloads folder)
- Username: `ubuntu`
- Host: `35.181.7.121`

**pgAdmin:**
- URL: http://35.181.7.121:5050
- Email: `admin@admin.com`
- Password: `admin`

**PostgreSQL Database:**
- Host: `airlines_postgresql` (internal) or `35.181.7.121` (external)
- Port: `5432`
- Database: `airlines_db`
- Username: `postgres`
- Password: `postgres`

**MongoDB:**
- Host: `mongodb` (internal) or `35.181.7.121` (external)
- Port: `27017`
- Username: `admin`
- Password: `admin123`
- Database: `airlines_db`

---

## Next Steps

### Immediate Actions:
1. ✅ Convert documentation to PDF
2. ✅ Bookmark dashboard URL
3. ✅ Test all service URLs
4. ✅ Verify data collection is running
5. ✅ Share URLs with team members

### Short Term (This Week):
- Monitor data collection logs
- Verify ML predictions are working
- Test API endpoints
- Train team members on dashboard
- Set up regular database backups

### Long Term (This Month):
- Review AWS costs
- Optimize performance if needed
- Consider upgrading instance if c7i-flex.large is insufficient
- Implement additional security measures
- Set up monitoring and alerts

---

## Support and Maintenance

### Daily:
- Monitor dashboard for new data
- Check that flight-collector is running

### Weekly:
- Review system logs
- Check disk space usage
- Verify backup creation

### Monthly:
- Review AWS billing
- Update Docker images
- Security patches
- Database optimization

---

## Project Information

**Deployment Date:** December 12, 2025
**AWS Region:** eu-west-3 (Paris)
**Instance Type:** c7i-flex.large (Free Tier)
**System Components:**
- PostgreSQL 17.4
- MongoDB 7.0
- Python 3.12
- FastAPI
- Dash (Plotly)
- Docker 28.2.2
- Docker Compose 5.0.0

**Data Sources:**
- Flight Data: airportinfo.live
- Weather Data: NOAA Aviation Weather (via API Ninjas)

**Machine Learning:**
- Algorithm: XGBoost
- Task: Binary classification (delay prediction)
- Accuracy: ~75-85%

---

## Contact Information

**Technical Support:**
- AWS Console: https://console.aws.amazon.com/
- Docker Docs: https://docs.docker.com/
- FastAPI Docs: https://fastapi.tiangolo.com/

**Project Resources:**
- Dashboard: http://35.181.7.121:8050
- API Docs: http://35.181.7.121:8000/docs
- pgAdmin: http://35.181.7.121:5050

---

*Documentation Package Version: 1.0*
*Created: December 12, 2025*
*Last Updated: December 12, 2025*

---

## License and Usage

This documentation is provided for the DST Airlines Flight Delay Prediction System.

**AWS Free Tier Notice:**
- Free for first 12 months with new AWS account
- Monitor usage to avoid unexpected charges
- Set up billing alerts in AWS Console

**Data Usage:**
- Flight data collected from public sources
- Weather data via API (free tier: 50K requests/month)
- Respect API rate limits
- No personal data collected

---

## Document Change Log

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-11 | Initial documentation creation | System |
| | | - AWS deployment configuration | |
| | | - Complete user guide | |
| | | - API documentation | |
| | | - Troubleshooting guide | |

---

**END OF DOCUMENTATION SUMMARY**
