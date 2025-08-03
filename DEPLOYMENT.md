# Deployment Guide

This guide covers deploying the Survey Question Translator MVP to production environments.

## Prerequisites

- Python 3.9 or higher
- pip (Python package installer)
- Git
- Web server (Nginx recommended)
- Process manager (systemd, supervisor, or PM2)

## Environment Setup

### 1. Server Preparation

#### Ubuntu/Debian
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install Nginx
sudo apt install nginx -y

# Install Git
sudo apt install git -y
```

#### CentOS/RHEL
```bash
# Update system
sudo yum update -y

# Install Python and pip
sudo yum install python3 python3-pip -y

# Install Nginx
sudo yum install nginx -y

# Install Git
sudo yum install git -y
```

### 2. Application Setup

```bash
# Clone the repository
git clone https://github.com/halderavik/OE_survey_questionnaire_translation.git
cd OE_survey_questionnaire_translation

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment file
cp .env.example .env

# Edit environment file
nano .env
```

Configure the following variables:

```bash
# DeepSeek API Configuration
DEEPSEEK_API_KEY=your_production_api_key_here

# Flask Configuration
SECRET_KEY=your_secure_secret_key_here
FLASK_ENV=production
FLASK_DEBUG=False

# Application Configuration
MAX_FILE_SIZE=2097152
MAX_QUESTIONS=1000

# Test Mode (must be false for production)
TEST_MODE=false
```

**Important Security Notes:**
- Generate a strong SECRET_KEY (use `python -c "import secrets; print(secrets.token_hex(32))"`)
- Use a production DeepSeek API key
- Set FLASK_DEBUG=False for production
- Set TEST_MODE=false for production

## Production Deployment

### 1. Using Gunicorn

#### Install Gunicorn
```bash
pip install gunicorn
```

#### Create Gunicorn Configuration
Create `gunicorn.conf.py`:

```python
# Gunicorn configuration file
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

#### Create Systemd Service
Create `/etc/systemd/system/survey-translator.service`:

```ini
[Unit]
Description=Survey Question Translator
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/path/to/OE_survey_questionnaire_translation
Environment=PATH=/path/to/OE_survey_questionnaire_translation/venv/bin
ExecStart=/path/to/OE_survey_questionnaire_translation/venv/bin/gunicorn --config gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### Start the Service
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable survey-translator

# Start service
sudo systemctl start survey-translator

# Check status
sudo systemctl status survey-translator
```

### 2. Using Supervisor

#### Install Supervisor
```bash
sudo apt install supervisor -y
```

#### Create Configuration
Create `/etc/supervisor/conf.d/survey-translator.conf`:

```ini
[program:survey-translator]
command=/path/to/OE_survey_questionnaire_translation/venv/bin/gunicorn --config gunicorn.conf.py app:app
directory=/path/to/OE_survey_questionnaire_translation
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/survey-translator/app.log
environment=PATH="/path/to/OE_survey_questionnaire_translation/venv/bin"
```

#### Start Supervisor
```bash
# Create log directory
sudo mkdir -p /var/log/survey-translator

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Start the application
sudo supervisorctl start survey-translator
```

### 3. Nginx Configuration

Create `/etc/nginx/sites-available/survey-translator`:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # File upload limits
    client_max_body_size 2M;

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 24h;
    }

    # Static files (if any)
    location /static/ {
        alias /path/to/OE_survey_questionnaire_translation/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

#### Enable the Site
```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/survey-translator /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

## SSL Certificate Setup

### Using Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Using Self-Signed Certificate (Development)

```bash
# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/survey-translator.key \
    -out /etc/ssl/certs/survey-translator.crt
```

## Monitoring and Logging

### 1. Application Logs

#### Gunicorn Logs
```bash
# View application logs
sudo journalctl -u survey-translator -f

# View supervisor logs
sudo tail -f /var/log/survey-translator/app.log
```

#### Nginx Logs
```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

### 2. System Monitoring

#### Install Monitoring Tools
```bash
# Install htop for system monitoring
sudo apt install htop -y

# Install netstat for network monitoring
sudo apt install net-tools -y
```

#### Monitor Application
```bash
# Check process status
ps aux | grep gunicorn

# Check port usage
netstat -tlnp | grep :8000

# Monitor system resources
htop
```

## Backup and Recovery

### 1. Application Backup

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/survey-translator"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup application files
tar -czf $BACKUP_DIR/app_$DATE.tar.gz \
    --exclude=venv \
    --exclude=__pycache__ \
    --exclude=.git \
    /path/to/OE_survey_questionnaire_translation

# Backup environment file
cp /path/to/OE_survey_questionnaire_translation/.env $BACKUP_DIR/env_$DATE

echo "Backup completed: $BACKUP_DIR/app_$DATE.tar.gz"
EOF

chmod +x backup.sh
```

### 2. Automated Backups

```bash
# Add to crontab
sudo crontab -e

# Add daily backup at 2 AM
0 2 * * * /path/to/backup.sh
```

## Performance Optimization

### 1. Gunicorn Tuning

Adjust `gunicorn.conf.py` based on your server:

```python
# For 4 CPU cores
workers = 4

# For high memory usage
worker_connections = 2000

# For better performance
worker_class = "gevent"
```

### 2. Nginx Optimization

Add to Nginx configuration:

```nginx
# Enable gzip compression
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

# Enable caching
location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Security Hardening

### 1. Firewall Configuration

```bash
# Install UFW
sudo apt install ufw -y

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

### 2. Application Security

- Use strong SECRET_KEY
- Set FLASK_DEBUG=False
- Use HTTPS only
- Implement rate limiting
- Regular security updates

### 3. Server Security

```bash
# Disable root login
sudo passwd -l root

# Create non-root user
sudo adduser deploy
sudo usermod -aG sudo deploy

# Configure SSH
sudo nano /etc/ssh/sshd_config
# Set: PermitRootLogin no
# Set: PasswordAuthentication no
```

## Troubleshooting

### Common Issues

1. **Application Not Starting**
   ```bash
   # Check logs
   sudo journalctl -u survey-translator -f
   
   # Check permissions
   sudo chown -R www-data:www-data /path/to/app
   ```

2. **Nginx 502 Bad Gateway**
   ```bash
   # Check if Gunicorn is running
   ps aux | grep gunicorn
   
   # Check port
   netstat -tlnp | grep :8000
   ```

3. **SSL Issues**
   ```bash
   # Test SSL configuration
   sudo nginx -t
   
   # Check certificate
   openssl x509 -in /path/to/cert.crt -text -noout
   ```

### Health Checks

```bash
# Application health
curl -f http://localhost:8000/test

# Nginx health
curl -f http://localhost/health

# SSL health
curl -f https://your-domain.com/test
```

## Scaling

### Horizontal Scaling

1. **Load Balancer**: Use HAProxy or Nginx as load balancer
2. **Multiple Instances**: Deploy multiple application instances
3. **Database**: Consider adding a database for session storage

### Vertical Scaling

1. **Increase Resources**: Add more CPU and RAM
2. **Optimize Code**: Profile and optimize application code
3. **Caching**: Implement Redis for caching

## Maintenance

### Regular Tasks

1. **Security Updates**: Weekly system updates
2. **Backup Verification**: Monthly backup testing
3. **Log Rotation**: Configure log rotation
4. **Performance Monitoring**: Monitor application performance

### Update Procedure

```bash
# Stop application
sudo systemctl stop survey-translator

# Backup current version
./backup.sh

# Pull latest code
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Restart application
sudo systemctl start survey-translator

# Verify deployment
curl -f http://localhost:8000/test
```

## Support

For deployment support and issues:
1. Check application logs
2. Verify configuration files
3. Test connectivity
4. Review system resources
5. Contact development team 