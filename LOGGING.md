# Logging Configuration Guide

## Overview

The AiRec API implements comprehensive logging to track application behavior, errors, and performance. All logs are stored in the `tmp/` directory with automatic rotation.

## Log Files

### Location
```
tmp/app.log          # Current log file
tmp/app.log.1        # First backup
tmp/app.log.2        # Second backup
...
tmp/app.log.5        # Fifth backup (oldest)
```

### Rotation Policy
- **Maximum file size**: 10 MB
- **Backup count**: 5 files
- **Total log storage**: ~50 MB maximum

When `app.log` reaches 10MB, it's rotated:
- `app.log` → `app.log.1`
- `app.log.1` → `app.log.2`
- Oldest file (`app.log.5`) is deleted

## Log Levels

Configure via `LOG_LEVEL` environment variable in `.env`:

### DEBUG
```env
LOG_LEVEL=DEBUG
```
Logs everything including:
- All HTTP requests (method, path, IP)
- All HTTP responses (status codes)
- Database queries
- Detailed application flow
- Debug messages from all modules

**Use for**: Development, troubleshooting

### INFO (Default)
```env
LOG_LEVEL=INFO
```
Logs important events:
- Application startup
- Extension initialization
- Blueprint registration
- Database operations
- User authentication events
- API endpoint calls
- Configuration changes

**Use for**: Production monitoring

### WARNING
```env
LOG_LEVEL=WARNING
```
Logs potential issues:
- Invalid authentication attempts
- Missing API keys
- 404 errors
- Bad request errors
- Deprecated feature usage

**Use for**: Production with minimal logging

### ERROR
```env
LOG_LEVEL=ERROR
```
Logs only errors:
- 500 Internal Server Errors
- Database failures
- External API failures
- Exception stack traces

**Use for**: Production with critical-only logging

## Log Format

Each log entry follows this format:
```
[2026-02-11 14:30:45] LEVEL in module: message
```

Example:
```
[2026-02-11 14:30:45] INFO in app: AiRec API Starting
[2026-02-11 14:30:45] INFO in app: Environment: development
[2026-02-11 14:30:45] DEBUG in auth: User login attempt: user@example.com
[2026-02-11 14:30:46] ERROR in database: Connection failed: timeout
```

## Configuration

### Environment Variables

Add to your `.env` file:
```env
# Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Custom log directory (optional, defaults to tmp/)
# LOG_DIR=/var/log/airec

# Custom log file name (optional, defaults to app.log)
# LOG_FILE=custom.log
```

### Code Configuration

In `config.py`:
```python
# Logging Configuration
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tmp')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5
LOG_FORMAT = '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
```

## What Gets Logged

### Application Lifecycle
- ✅ Application startup
- ✅ Configuration loading
- ✅ Extension initialization
- ✅ Blueprint registration
- ✅ Database connection
- ✅ Server start/stop

### Authentication
- ✅ User registration
- ✅ Login attempts (successful/failed)
- ✅ Token generation
- ✅ Token validation
- ✅ Logout events
- ✅ Unauthorized access attempts

### API Requests (DEBUG level)
- ✅ HTTP method and path
- ✅ Client IP address
- ✅ Response status code
- ✅ Request parameters

### Database Operations
- ✅ Connection status
- ✅ Table creation
- ✅ Migration events
- ✅ Query errors

### Errors
- ✅ 400 Bad Request
- ✅ 401 Unauthorized
- ✅ 404 Not Found
- ✅ 500 Internal Server Error
- ✅ Exception stack traces
- ✅ Database errors
- ✅ External API errors

### External Services
- ✅ LLM API calls
- ✅ TMDB API calls
- ✅ Redis operations (if enabled)

## Viewing Logs

### Real-time Monitoring
```bash
# Follow live logs
tail -f tmp/app.log

# Follow with filtering
tail -f tmp/app.log | grep ERROR

# Last 100 lines
tail -n 100 tmp/app.log
```

### Search Logs
```bash
# Search for specific term
grep "user@example.com" tmp/app.log

# Search for errors
grep "ERROR" tmp/app.log

# Search with line numbers
grep -n "500" tmp/app.log

# Search across all log files
grep -h "ERROR" tmp/app.log*
```

### View by Date/Time
```bash
# View logs from specific date
grep "2026-02-11" tmp/app.log

# View logs from specific hour
grep "2026-02-11 14:" tmp/app.log
```

### Count Events
```bash
# Count errors
grep -c "ERROR" tmp/app.log

# Count by level
grep "INFO" tmp/app.log | wc -l
grep "WARNING" tmp/app.log | wc -l
grep "ERROR" tmp/app.log | wc -l
```

## Log Analysis Examples

### Find Failed Login Attempts
```bash
grep "Invalid email or password" tmp/app.log
```

### Find Internal Errors
```bash
grep "500 Internal Server Error" tmp/app.log
```

### Find Unauthorized Access
```bash
grep "Unauthorized access attempt" tmp/app.log
```

### Find Slow Requests (if timing is logged)
```bash
grep "took.*ms" tmp/app.log | sort -t: -k4 -n
```

### Monitor Specific User
```bash
grep "user_id: 123" tmp/app.log
```

## Custom Logging in Code

### In Route Handlers
```python
from flask import current_app

@app.route('/api/custom')
def custom_endpoint():
    current_app.logger.info('Custom endpoint called')
    
    try:
        # Your code
        result = process_data()
        current_app.logger.debug(f'Processed result: {result}')
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f'Processing failed: {str(e)}', exc_info=True)
        return jsonify({'error': 'Processing failed'}), 500
```

### In Service Classes
```python
import logging

class MyService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process(self):
        self.logger.info('Starting process')
        try:
            # Your code
            pass
        except Exception as e:
            self.logger.error(f'Error: {str(e)}', exc_info=True)
            raise
```

### Log Levels in Code
```python
from flask import current_app

# Debug - detailed information
current_app.logger.debug('Variable value: %s', variable)

# Info - general information
current_app.logger.info('User %s logged in', user_id)

# Warning - something unexpected
current_app.logger.warning('API key not configured')

# Error - serious problem
current_app.logger.error('Database connection failed', exc_info=True)

# Critical - application may crash
current_app.logger.critical('Out of memory')
```

## Production Best Practices

### 1. Set Appropriate Log Level
```env
# Production
LOG_LEVEL=INFO

# Development
LOG_LEVEL=DEBUG
```

### 2. Monitor Log Files
```bash
# Set up log rotation monitoring
watch -n 60 'ls -lh tmp/app.log*'

# Alert on errors
watch -n 300 'grep -c ERROR tmp/app.log'
```

### 3. Archive Old Logs
```bash
# Compress old logs
gzip tmp/app.log.5

# Move to archive
mv tmp/app.log.*.gz /archive/logs/$(date +%Y-%m)/
```

### 4. Set Up Log Aggregation
Consider using:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **Datadog**
- **CloudWatch** (AWS)
- **Stackdriver** (GCP)

### 5. Log Rotation Script
```bash
#!/bin/bash
# rotate_logs.sh
LOG_DIR="tmp"
ARCHIVE_DIR="/archive/logs"

# Create archive directory
mkdir -p "$ARCHIVE_DIR/$(date +%Y-%m)"

# Compress and move logs older than 7 days
find "$LOG_DIR" -name "app.log.*" -mtime +7 -exec gzip {} \;
find "$LOG_DIR" -name "app.log.*.gz" -exec mv {} "$ARCHIVE_DIR/$(date +%Y-%m)/" \;
```

## Troubleshooting

### Logs Not Being Created
```bash
# Check directory exists
ls -la tmp/

# Check permissions
chmod 755 tmp/

# Check disk space
df -h

# Manually create directory
mkdir -p tmp/
```

### Logs Not Rotating
```bash
# Check file size
ls -lh tmp/app.log

# Check configuration
grep LOG_MAX_BYTES config.py

# Force rotation by renaming
mv tmp/app.log tmp/app.log.manual
# Restart application
```

### Permission Errors
```bash
# Fix ownership
chown -R www-data:www-data tmp/

# Fix permissions
chmod -R 755 tmp/
```

### Too Many Logs
```bash
# Reduce log level
LOG_LEVEL=WARNING  # or ERROR

# Increase rotation size
LOG_MAX_BYTES = 50 * 1024 * 1024  # 50MB

# Reduce backup count
LOG_BACKUP_COUNT = 3
```

## Security Considerations

### Don't Log Sensitive Data
```python
# ❌ BAD - logs password
logger.info(f'User login: {email} with password {password}')

# ✅ GOOD - no sensitive data
logger.info(f'User login attempt: {email}')
```

### Sanitize User Input
```python
# ❌ BAD - logs raw user input
logger.info(f'Search query: {user_input}')

# ✅ GOOD - sanitize or truncate
logger.info(f'Search query: {user_input[:50]}...')
```

### Protect Log Files
```bash
# Restrict access
chmod 600 tmp/app.log

# Only application user can read
chown www-data:www-data tmp/app.log
```

## Performance Impact

- **DEBUG level**: ~5-10% performance overhead
- **INFO level**: ~1-2% performance overhead
- **WARNING/ERROR**: Minimal overhead

**Recommendation**: Use INFO in production, DEBUG only when troubleshooting.

## Integration with Monitoring Tools

### Example: Send errors to Sentry
```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FlaskIntegration()],
    environment="production"
)
```

### Example: Send logs to CloudWatch
```python
import watchtower

cloudwatch_handler = watchtower.CloudWatchLogHandler()
app.logger.addHandler(cloudwatch_handler)
```

## Summary

✅ Logs stored in `tmp/app.log`
✅ Automatic rotation at 10MB
✅ 5 backup files retained
✅ Configurable log levels
✅ Request/response tracking
✅ Error tracking with stack traces
✅ Authentication event logging
✅ Production-ready configuration

For more information, see the main README.md or contact support.
