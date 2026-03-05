# Systemd Service for AI Token Analyzer Upload

## Overview

This document describes how to set up the AI Token Analyzer upload service to run automatically in the background on remote machines.

## Architecture

```
┌─────────────────┐           ┌─────────────────┐
│  Remote Machine │  ──────►  │  Central Server │
│                 │   HTTPS   │                 │
│  - Fetch data   │   POST    │  - Store data   │
│  - Upload data  │  /api/... │  - Serve UI     │
└─────────────────┘           └─────────────────┘
```

## Setup on Remote Machine

### 1. Install the upload script

Copy `scripts/upload_to_server.py` to the remote machine:
```bash
scp scripts/upload_to_server.py user@remote:/opt/ai-token-analyzer/scripts/
```

### 2. Configure the upload service

Copy the service file:
```bash
sudo cp contrib/upload-service.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/ai-token-upload.service
```

### 3. Edit the service configuration

```bash
sudo nano /etc/systemd/system/ai-token-upload.service
```

Update these environment variables:
```ini
Environment="UPLOAD_SERVER=http://your-server:5001"
Environment="UPLOAD_AUTH_KEY=your-secure-auth-key"
Environment="UPLOAD_HOSTNAME=remote-machine-01"
```

### 4. Enable and start the service

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-token-upload
sudo systemctl start ai-token-upload
```

### 5. Verify it's running

```bash
# Check status
sudo systemctl status ai-token-upload

# View logs
journalctl -u ai-token-upload -f

# Test manually (without daemon)
python3 scripts/upload_to_server.py \
    --server http://your-server:5001 \
    --auth-key your-auth-key \
    --hostname remote-machine-01 \
    --interval 30
```

## Service Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `UPLOAD_SERVER` | Server URL to upload to | Required |
| `UPLOAD_AUTH_KEY` | Authentication key for server | Required |
| `UPLOAD_HOSTNAME` | Hostname to ID this machine | System hostname |

### Service Parameters

Edit the `ExecStart` line to customize:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--interval` | Upload frequency (seconds) | `--interval 60` (every 60s) |
| `--incremental` | Only upload new data | Enabled by default |
| `--tool` | Specific tool to upload | `--tool claude` |
| `--no-incremental` | Upload all data each time | Disable incremental |

### Example: More Frequent Uploads

For 15-second intervals:
```ini
ExecStart=/usr/bin/python3 /opt/ai-token-analyzer/scripts/upload_to_server.py \
    --server ${UPLOAD_SERVER} \
    --auth-key ${UPLOAD_AUTH_KEY} \
    --hostname ${UPLOAD_HOSTNAME} \
    --daemon \
    --interval 15 \
    --incremental
```

### Example: Single Tool

Upload only Claude data:
```ini
ExecStart=/usr/bin/python3 /opt/ai-token-analyzer/scripts/upload_to_server.py \
    --server ${UPLOAD_SERVER} \
    --auth-key ${UPLOAD_AUTH_KEY} \
    --hostname ${UPLOAD_HOSTNAME} \
    --daemon \
    --interval 30 \
    --incremental \
    --tool claude
```

## Management Commands

```bash
# Check service status
sudo systemctl status ai-token-upload

# Start the service
sudo systemctl start ai-token-upload

# Stop the service
sudo systemctl stop ai-token-upload

# Restart the service (after config changes)
sudo systemctl restart ai-token-upload

# View logs in real-time
journalctl -u ai-token-upload -f

# View logs from today
journalctl -u ai-token-upload --since "today"

# Disable auto-start
sudo systemctl disable ai-token-upload
```

## Verifying Upload

### Check on Server

```bash
# On the central server, check uploaded data
python3 -c "
import sys
sys.path.insert(0, 'scripts/shared')
from db import get_all_hosts, get_summary_by_tool

print('Hosts:', get_all_hosts())

for host in get_all_hosts():
    summary = get_summary_by_tool(host)
    print(f'\n{host}:')
    for tool, stats in summary.items():
        print(f'  {tool}: {stats[\"total_tokens\"]} tokens')
"
```

### Check Upload History (Local)

The upload marker file tracks last upload time:
```bash
cat ~/.ai-token-analyzer/upload_marker.json
```

Example output:
```json
{
  "remote-machine-01": {
    "last_upload": "2024-01-15T10:30:00",
    "timestamp": "2024-01-15T10:30:01.123456"
  }
}
```

## Troubleshooting

### Service won't start

```bash
# Check logs
journalctl -u ai-token-upload -n 50

# Common issues:
# 1. Invalid server URL - check UPLOAD_SERVER
# 2. Invalid auth key - check UPLOAD_AUTH_KEY
# 3. Network connectivity - verify server is reachable
```

### Data not appearing on server

```bash
# Test upload manually (with verbose output)
python3 scripts/upload_to_server.py \
    --server http://your-server:5001 \
    --auth-key your-auth-key \
    --hostname your-machine \
    --days 1 \
    --verbose

# Check if data exists locally
python3 -c "
import sys
sys.path.insert(0, 'scripts/shared')
from db import get_usage_by_date
print(get_usage_by_date('2024-01-15'))
"
```

### Memory/CPU concerns

Edit the service file to limit resources:
```ini
MemoryLimit=256M
CPUQuota=25%
```

## Security Considerations

1. **Use HTTPS**: Configure your server with SSL and use `https://` in the URL
2. **Strong Auth Key**: Use a unique, cryptographically secure auth key for each machine
3. **Network Security**: Consider firewall rules to restrict upload endpoint access
4. **File Permissions**: Keep service file readable only by root
   ```bash
   sudo chmod 644 /etc/systemd/system/ai-token-upload.service
   ```

## Multiple Machines

Each remote machine should have:
- Unique `UPLOAD_HOSTNAME` (e.g., `macbook-pro`, `server-01`)
- Unique `UPLOAD_AUTH_KEY` for security
- Same `UPLOAD_SERVER` pointing to central server

Example for 3 machines:

| Machine | Hostname | Auth Key |
|---------|----------|----------|
| Machine 1 | `macbook-pro` | `key-for-macbook` |
| Machine 2 | `server-01` | `key-for-server01` |
| Machine 3 | `vm-aws` | `key-for-aws-vm` |

## Alternative: Manual Upload

For one-time uploads (not daemon mode):
```bash
python3 scripts/upload_to_server.py \
    --server http://your-server:5001 \
    --auth-key your-auth-key \
    --hostname your-machine \
    --days 7
```

For cron-based periodic uploads:
```bash
# Add to crontab (crontab -e)
# Upload every 30 minutes
*/30 * * * * /usr/bin/python3 /opt/ai-token-analyzer/scripts/upload_to_server.py \
    --server http://your-server:5001 \
    --auth-key your-auth-key \
    --hostname your-machine \
    --days 1 > /var/log/ai-upload.log 2>&1
```
