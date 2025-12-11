# AWS Deployment Configuration Guide
## DST Airlines - Flight Delay Prediction System

---

## Table of Contents
1. [AWS Infrastructure Setup](#aws-infrastructure-setup)
2. [EC2 Instance Configuration](#ec2-instance-configuration)
3. [Security Group Rules](#security-group-rules)
4. [Docker Installation](#docker-installation)
5. [Application Configuration](#application-configuration)
6. [Environment Variables](#environment-variables)
7. [Database Setup](#database-setup)
8. [Troubleshooting](#troubleshooting)

---

## AWS Infrastructure Setup

### EC2 Instance Details

**Instance Information:**
- **Instance Type:** t2.micro (Free Tier)
- **vCPU:** 1
- **Memory:** 1 GiB
- **Storage:** 25 GB gp3 (Free Tier eligible up to 30GB)
- **Operating System:** Ubuntu Server 22.04 LTS
- **Region:** eu-west-3 (Paris)

**Instance Identifiers:**
- **Public IPv4 Address:** 13.37.217.206
- **Public IPv4 DNS:** ec2-13-37-217-206.eu-west-3.compute.amazonaws.com
- **Instance Name:** airlines-app-server (or your chosen name)

**SSH Key Pair:**
- **Key Name:** airlines-key
- **Key Type:** RSA
- **Format:** .pem (for Mac/Linux/Windows PowerShell)
- **Location:** Downloads folder
- **Permissions:** Read-only for owner (0400 or equivalent)

---

## EC2 Instance Configuration

### Launch Configuration

1. **AMI Selection:**
   - Ubuntu Server 22.04 LTS (HVM), SSD Volume Type
   - Free tier eligible

2. **Instance Type:**
   - t2.micro (1 vCPU, 1 GiB RAM)
   - Note: For production with heavy load, consider t3.small or larger

3. **Network Settings:**
   - Auto-assign public IP: **Enabled**
   - VPC: Default VPC
   - Subnet: Default subnet (auto-assigned)

4. **Storage Configuration:**
   - Volume Type: gp3 (General Purpose SSD)
   - Size: 25 GiB
   - Delete on Termination: Yes
   - Encryption: No (optional for security)

---

## Security Group Rules

### Security Group Name
`airlines-security-group`

### Inbound Rules Configuration

| Rule # | Type | Protocol | Port Range | Source | Description |
|--------|------|----------|------------|--------|-------------|
| 1 | SSH | TCP | 22 | My IP | SSH access for administration |
| 2 | Custom TCP | TCP | 5432 | 0.0.0.0/0 | PostgreSQL database access |
| 3 | Custom TCP | TCP | 27017 | 0.0.0.0/0 | MongoDB database access |
| 4 | Custom TCP | TCP | 8000 | 0.0.0.0/0 | FastAPI REST API |
| 5 | Custom TCP | TCP | 8050 | 0.0.0.0/0 | Dash Dashboard web interface |
| 6 | Custom TCP | TCP | 5050 | 0.0.0.0/0 | pgAdmin database management |

### Outbound Rules
- **Type:** All traffic
- **Protocol:** All
- **Port Range:** All
- **Destination:** 0.0.0.0/0

### Security Recommendations

**For Production Environments:**
- Change SSH source from "My IP" to specific trusted IPs only
- Restrict database ports (5432, 27017, 5050) to specific IP ranges
- Enable VPC firewall rules for additional security
- Use AWS Security Groups in combination with application-level authentication
- Consider using AWS Systems Manager Session Manager instead of direct SSH
- Enable CloudWatch logging for security monitoring

---

## Docker Installation

### Software Versions Installed

```
Docker version: 28.2.2
Docker Compose version: v5.0.0
```

### Installation Commands Used

```bash
# Update system packages
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add user to Docker group (no sudo required)
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make Docker Compose executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version
```

---

## Application Configuration

### Project Directory Structure

```
/home/ubuntu/projet-avril25_cde_airlines-dockerisation/
├── .env                          # Environment configuration (created)
├── .env.default                  # Template configuration
├── docker-compose.yml            # Docker services definition
├── Makefile                      # Automation commands
├── README.md                     # Project documentation
├── airlines-dbt-postgres/        # DBT data transformation
│   ├── dbt/                      # DBT models and seeds
│   └── dbt_prepare/              # Data preparation scripts
├── flight-collector/             # Python flight data collector
│   ├── config/                   # Configuration files
│   ├── data/                     # Data collection modules
│   ├── orchestration/            # Execution management
│   ├── machine_learning/         # ML models for predictions
│   ├── utils/                    # Utility functions
│   ├── Dockerfile                # Container definition
│   ├── main.py                   # Application entry point
│   └── requirements.txt          # Python dependencies
└── web/                          # Web services
    ├── FastAPI/                  # REST API
    │   ├── Dockerfile
    │   ├── main.py
    │   └── requirements.txt
    └── dash/                     # Dashboard application
        ├── Dockerfile
        ├── app.py
        ├── pages/                # Dashboard pages
        └── requirements.txt
```

---

## Environment Variables

### .env Configuration File

**Location:** `/home/ubuntu/projet-avril25_cde_airlines-dockerisation/.env`

### Database Connections

```bash
# MongoDB Configuration
MONGODB_URI=mongodb://admin:admin123@mongodb:27017/
MONGODB_DATABASE=airlines_db

# PostgreSQL Configuration
POSTGRESQL_URI=postgresql://postgres:postgres@postgresql:5432/airlines_db
ENABLE_POSTGRESQL_INSERTION=true
```

**Important Notes:**
- Hostnames use Docker service names (mongodb, postgresql) not localhost
- These are internal Docker network connections
- Credentials match docker-compose.yml definitions

### DBT Configuration

```bash
# DBT Data Transformation
DBT_SOURCE_DIR=./airlines-dbt-postgres/data
DBT_TARGET_DIR=./airlines-dbt-postgres/dbt/seeds
API_NINJAS_KEY=votre_cle_api_ninjas
```

**API Ninjas Key:**
- Required for weather data collection
- Sign up at: https://api-ninjas.com/
- Free tier: 50,000 requests/month
- Optional: Can run without weather data

### Machine Learning Configuration

```bash
# ML Model Settings
ML_MODEL_DIR=machine_learning/model_output
ENABLE_ML_PREDICTION=true
```

### Data Collection Settings

```bash
# Collection Parameters
NUM_AIRPORTS=200              # Number of airports to monitor
DELAY=1.5                     # Delay between requests (seconds)
BATCH_SIZE=500                # Records per batch
ENABLE_WEATHER=true           # Collect METAR/TAF weather data
HOUR_OFFSET=1                 # Future hours for real-time collection
PAST_HOUR_OFFSET=-20          # Past hours for historical collection
```

### Execution Behavior

```bash
# Behavior Configuration
RUN_ONCE=false                     # false = continuous loop mode
COLLECT_REALTIME=true              # Collect current/future flights
COLLECT_PAST=true                  # Collect historical flights
SCHEDULE_MINUTE=35                 # Execute at XX:35 each cycle
LOOP_INTERVAL_MINUTES=60           # Cycle every 60 minutes
```

**Scheduling Details:**
- Runs every hour at minute 35 (e.g., 15:35, 16:35, 17:35)
- Collects both real-time and historical data each cycle
- Set RUN_ONCE=true for single execution (testing)

### Logging Configuration

```bash
# Logging Settings
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR
LOG_TO_CONSOLE=true           # Print to console
LOG_TO_FILE=true              # Write to log files
```

### FTP Upload (Optional)

```bash
# FTP Configuration (Disabled by default)
ENABLE_FTP_UPLOAD=false
FTP_HOST=7k0n6.ftp.infomaniak.com
FTP_PORT=21
FTP_USERNAME=7k0n6_dst
FTP_PASSWORD=votre_mot_de_passe_ftp
FTP_USE_TLS=false
FTP_REMOTE_DIRECTORY=/data
```

### Cache Server (Optional)

```bash
# External Cache Server
USE_CACHE_SERVER=true
CACHE_SERVER_URL=https://dst.devlab.app/index.php
```

### Metadata

```bash
# Application Metadata
SCRIPT_VERSION=2.0
SOURCE=airportinfo.live
```

---

## Database Setup

### PostgreSQL Configuration

**Container Details:**
- Image: postgres:17.4
- Container Name: airlines_postgresql
- Port: 5432 (mapped to host)
- Network: airlines_network

**Credentials:**
- Username: postgres
- Password: postgres
- Database: airlines_db

**Initialization:**
- Auto-creates database on first start
- Runs init script: `flight-collector/utils/dst_postgresql.sql`
- Creates all required tables and schemas
- Persistent storage: Docker volume `postgresql_data`

**Health Check:**
- Command: `pg_isready -U postgres`
- Interval: 10 seconds
- Timeout: 5 seconds
- Retries: 5

### MongoDB Configuration

**Container Details:**
- Image: mongo:7.0
- Container Name: airlines_mongodb
- Port: 27017 (mapped to host)
- Network: airlines_network

**Credentials:**
- Root Username: admin
- Root Password: admin123
- Database: airlines_db

**Storage:**
- Data volume: mongodb_data
- Config volume: mongodb_config

**Health Check:**
- Command: `mongosh --eval "db.adminCommand('ping')"`
- Interval: 10 seconds
- Timeout: 5 seconds
- Retries: 5

### pgAdmin Configuration

**Container Details:**
- Image: dpage/pgadmin4:latest
- Container Name: airlines_pgadmin
- Port: 5050 (mapped to host port 80)
- Network: airlines_network

**Login Credentials:**
- Email: admin@admin.com
- Password: admin

**Manual Database Connection Setup:**
1. Open http://13.37.217.206:5050
2. Login with credentials above
3. Right-click "Servers" → Register → Server
4. General tab:
   - Name: Airlines PostgreSQL
5. Connection tab:
   - Host: airlines_postgresql (or 172.18.0.4)
   - Port: 5432
   - Database: airlines_db
   - Username: postgres
   - Password: postgres
   - Save password: ✓

---

## Docker Services

### Service Overview

```yaml
# All services defined in docker-compose.yml
services:
  - postgresql      # Database (port 5432)
  - mongodb         # NoSQL database (port 27017)
  - flight-collector # Data collection app
  - fastapi         # REST API (port 8000)
  - dash            # Dashboard (port 8050)
  - pgadmin         # DB admin tool (port 5050)
  - dbt             # Data transformation (runs then exits)
  - dbt_prepare     # Data preparation (runs then exits)
```

### Docker Compose Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v

# View service status
docker-compose ps

# View logs (all services)
docker-compose logs -f

# View logs (specific service)
docker-compose logs -f flight-collector

# Restart a specific service
docker-compose restart fastapi

# Rebuild and restart
docker-compose up -d --build

# Stop without removing containers
docker-compose stop

# Start stopped containers
docker-compose start
```

### Using Makefile Commands

```bash
# View all available commands
make help

# Start all services
make up

# Stop all services
make down

# View logs
make logs

# Clean everything (remove volumes)
make clean

# Run complete setup (start + DBT pipeline)
make all

# DBT commands
make dbt-prepare    # Prepare seed data
make dbt-seed       # Load seeds into DB
make dbt-run        # Run transformations
make dbt-all        # Complete DBT pipeline

# Web services
make web-build      # Rebuild FastAPI and Dash
make web-up         # Start web services only
make web-down       # Stop web services
make web-logs       # View web service logs
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Services Not Starting

**Check container status:**
```bash
docker-compose ps
```

**View detailed logs:**
```bash
docker-compose logs [service-name]
```

**Restart specific service:**
```bash
docker-compose restart [service-name]
```

#### 2. Database Connection Errors

**Check database is healthy:**
```bash
docker-compose ps
# Look for "healthy" status on postgresql and mongodb
```

**Verify environment variables:**
```bash
cat .env | grep URI
# Ensure hostnames use service names (mongodb, postgresql)
```

**Test PostgreSQL connection:**
```bash
docker exec -it airlines_postgresql psql -U postgres -d airlines_db
```

#### 3. Out of Memory Errors

**t2.micro has only 1GB RAM - may be insufficient**

**Check memory usage:**
```bash
docker stats
```

**Solutions:**
- Stop unnecessary services temporarily
- Upgrade to t3.small (2GB RAM, ~$15/month)
- Reduce NUM_AIRPORTS in .env
- Set ENABLE_WEATHER=false

#### 4. Port Already in Use

**Find what's using the port:**
```bash
sudo lsof -i :8000  # Replace 8000 with your port
```

**Kill the process or change port in docker-compose.yml**

#### 5. Disk Space Full

**Check disk usage:**
```bash
df -h
```

**Clean Docker resources:**
```bash
docker system prune -a --volumes
```

**Increase EBS volume size in AWS console**

#### 6. Permission Denied Errors

**Ensure user is in docker group:**
```bash
groups
# Should show "docker" in the list
```

**If not, re-add and reconnect:**
```bash
sudo usermod -aG docker ubuntu
exit
# Reconnect via SSH
```

#### 7. Flight Collector Not Collecting Data

**Check logs for errors:**
```bash
docker-compose logs -f flight-collector
```

**Common issues:**
- Waiting for scheduled time (check next execution time)
- API rate limiting (reduce NUM_AIRPORTS or increase DELAY)
- API_NINJAS_KEY missing (add key or disable weather)

#### 8. pgAdmin Can't Connect to PostgreSQL

**Password authentication failed:**
- Manually add server connection in pgAdmin UI
- Use credentials: postgres/postgres
- Host: airlines_postgresql or container IP

**Find container IP:**
```bash
docker inspect airlines_postgresql | grep IPAddress
```

---

## Backup and Maintenance

### Database Backups

**PostgreSQL Backup:**
```bash
docker exec airlines_postgresql pg_dump -U postgres airlines_db > backup.sql
```

**PostgreSQL Restore:**
```bash
cat backup.sql | docker exec -i airlines_postgresql psql -U postgres -d airlines_db
```

**MongoDB Backup:**
```bash
docker exec airlines_mongodb mongodump --uri="mongodb://admin:admin123@localhost:27017" --out=/backup
docker cp airlines_mongodb:/backup ./mongodb_backup
```

### Monitoring

**View resource usage:**
```bash
docker stats
```

**Check disk space:**
```bash
df -h
du -sh /var/lib/docker
```

**View system logs:**
```bash
sudo journalctl -u docker -f
```

### Updates

**Update Docker images:**
```bash
docker-compose pull
docker-compose up -d
```

**Update application code:**
```bash
# On local machine
scp -i ~/Downloads/airlines-key.pem -r ./projet-avril25_cde_airlines-dockerisation ubuntu@13.37.217.206:~/

# On EC2
cd projet-avril25_cde_airlines-dockerisation
docker-compose down
docker-compose up -d --build
```

---

## Security Best Practices

### AWS Security

1. **Regularly update SSH key pair locations**
2. **Enable AWS CloudWatch for monitoring**
3. **Set up AWS Config for compliance**
4. **Use IAM roles instead of access keys when possible**
5. **Enable VPC Flow Logs**
6. **Regular security group audits**

### Application Security

1. **Change default passwords in .env:**
   - PostgreSQL: postgres/postgres
   - MongoDB: admin/admin123
   - pgAdmin: admin@admin.com/admin

2. **Use environment-specific .env files:**
   - .env.development
   - .env.production

3. **Enable HTTPS with Let's Encrypt:**
   - Install Nginx reverse proxy
   - Configure SSL certificates
   - Redirect HTTP to HTTPS

4. **Implement rate limiting in FastAPI**

5. **Add authentication to API endpoints**

6. **Regular dependency updates:**
```bash
pip list --outdated  # Check for updates
```

### Network Security

1. **Restrict database ports to application servers only**
2. **Use AWS VPC private subnets for databases**
3. **Enable AWS WAF for web services**
4. **Set up CloudFront CDN for DDoS protection**
5. **Regular security patching:**
```bash
sudo apt-get update
sudo apt-get upgrade
```

---

## Cost Optimization

### Free Tier Limits

- **EC2 t2.micro:** 750 hours/month (1 instance running 24/7)
- **EBS Storage:** 30 GB/month
- **Data Transfer:** 15 GB outbound/month
- **Exceeding limits will incur charges**

### Monthly Cost Estimates (After Free Tier)

| Resource | Cost/Month |
|----------|------------|
| t2.micro EC2 (24/7) | $0 (Free tier) or ~$8.50 |
| t3.small EC2 (24/7) | ~$15 |
| 25 GB EBS gp3 | $2 |
| Data Transfer (100GB) | $9 |
| **Total (Free tier)** | **$0-2** |
| **Total (t3.small)** | **~$26** |

### Cost Reduction Tips

1. **Stop instance when not in use:**
```bash
aws ec2 stop-instances --instance-ids i-xxxxx
```

2. **Use AWS Lambda for scheduled tasks instead of 24/7 running**

3. **Set up CloudWatch alarms for billing**

4. **Use S3 for logs instead of EBS storage**

5. **Implement auto-scaling only when needed**

---

## Contact and Support

**Project Repository:** (Add your GitHub URL here)

**AWS Support:** https://console.aws.amazon.com/support/

**Docker Documentation:** https://docs.docker.com/

**PostgreSQL Documentation:** https://www.postgresql.org/docs/

**MongoDB Documentation:** https://www.mongodb.com/docs/

---

*Document Version: 1.0*
*Last Updated: December 11, 2025*
*Deployment Date: December 11, 2025*
