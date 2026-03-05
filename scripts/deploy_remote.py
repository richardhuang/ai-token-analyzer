#!/usr/bin/env python3
"""
Deploy AI Token Analyzer to remote machine.
This script copies the necessary files and sets up the upload service.
"""

import argparse
import subprocess
import sys
import os
import json

# Add shared directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
shared_dir = os.path.join(script_dir)
if shared_dir not in sys.path:
    sys.path.insert(0, shared_dir)

from shared.config import CONFIG_DIR, REMOTE_USER


def run_cmd(cmd, capture=True, check=True):
    """Run a shell command."""
    print(f"  $ {cmd}")
    if capture:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        if result.stdout:
            print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, end='')
        return result
    else:
        return subprocess.run(cmd, shell=True, check=check)


def main():
    parser = argparse.ArgumentParser(
        description='Deploy AI Token Analyzer to remote machine',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('host', help='Remote host IP or hostname')
    parser.add_argument('--user', default=REMOTE_USER, help=f'Remote user (default: {REMOTE_USER})')
    parser.add_argument('--server-url', default='http://localhost:5001', help='Server URL')
    parser.add_argument('--auth-key', default=None, required=True, help='Authentication key for upload')
    parser.add_argument('--hostname', default=None, help='Hostname to use (default: remote hostname)')
    parser.add_argument('--no-setup-service', action='store_true', help='Skip systemd service setup')
    parser.add_argument('--no-start', action='store_true', help='Do not start the service after setup')

    args = parser.parse_args()

    print(f"=== Deploying to {args.user}@{args.host} ===\n")

    # Step 1: Check SSH connection
    print("1. Testing SSH connection...")
    result = run_cmd(f"ssh root@{args.host} 'echo Connection OK'")
    if result.returncode != 0:
        print(f"Error: Cannot connect to {args.host}")
        sys.exit(1)
    print("✓ SSH connection successful\n")

    # Step 2: Get remote hostname if not specified
    if not args.hostname:
        result = run_cmd(f"ssh root@{args.host} 'hostname'", capture=True)
        if result.returncode == 0:
            args.hostname = result.stdout.strip()
            print(f"Remote hostname: {args.hostname}")
        else:
            args.hostname = args.host
            print(f"Using {args.host} as hostname")
    print()

    # Step 3: Check Python and dependencies
    print("2. Checking Python and dependencies...")
    result = run_cmd(f"ssh root@{args.host} 'python3 --version'")
    if result.returncode != 0:
        print("Error: Python3 not found")
        sys.exit(1)

    # Check if flask is installed
    result = run_cmd(f"ssh root@{args.host} 'python3 -c \"import flask\" 2>/dev/null && echo OK'")
    if result.returncode != 0:
        print("Installing Flask...")
        run_cmd(f"ssh root@{args.host} 'pip3 install flask'", check=False)
    print("✓ Python and dependencies OK\n")

    # Step 4: Copy ai-token-analyzer to remote
    print("3. Copying ai-token-analyzer to remote machine...")
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__)) + '/../'
    project_root = os.path.abspath(project_root)

    # Create remote directory
    run_cmd(f"ssh root@{args.host} 'mkdir -p /opt/ai-token-analyzer'")
    run_cmd(f"ssh root@{args.host} 'chown -R {args.user}:{args.user} /opt/ai-token-analyzer'")

    # Copy files
    print("  Copying files...")
    files_to_copy = [
        'cli.py',
        'web.py',
        'config/',
        'scripts/',
        'templates/',
        'static/',
    ]

    # Use rsync if available, otherwise use scp
    result = run_cmd("which rsync", capture=True)
    if result.returncode == 0:
        # Use rsync for efficient transfer
        exclude_patterns = ['*.pyc', '__pycache__', '*.db', '.git', 'venv', 'env']
        excludes = ' '.join([f'--exclude="{p}"' for p in exclude_patterns])
        run_cmd(f"rsync -avz {excludes} {project_root}/* root@{args.host}:/opt/ai-token-analyzer/")
    else:
        # Use tar for efficient transfer
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as f:
            tar_file = f.name

        # Create tarball locally
        import tarfile
        with tarfile.open(tar_file, 'w:gz') as tar:
            tar.add(project_root, arcname='ai-token-analyzer', exclude=lambda x: any(p in x for p in ['*.pyc', '__pycache__', '*.db', '.git', 'venv', 'env']))

        # Copy tarball to remote
        run_cmd(f"scp {tar_file} root@{args.host}:/tmp/ai-token-analyzer.tar.gz")
        run_cmd(f"ssh root@{args.host} 'tar -xzf /tmp/ai-token-analyzer.tar.gz -C /opt/ && rm /tmp/ai-token-analyzer.tar.gz'")

        os.unlink(tar_file)

    print("✓ Files copied\n")

    # Step 5: Create config file on remote
    print("4. Creating configuration on remote machine...")

    import tempfile
    # Create temp config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "host_name": args.hostname,
            "server": {
                "upload_auth_key": args.auth_key,
                "server_url": args.server_url
            },
            "tools": {
                "openclaw": {
                    "enabled": True,
                    "token_env": "OPENCLAW_TOKEN",
                    "gateway_url": "http://127.0.0.1:18789"
                },
                "claude": {
                    "enabled": True
                },
                "qwen": {
                    "enabled": True
                }
            },
            "cron": {
                "enabled": True,
                "run_time": "00:30"
            }
        }, f)
        temp_config = f.name

    # Copy config to remote
    run_cmd(f"scp {temp_config} root@{args.host}:/tmp/config.json")
    run_cmd(f"ssh root@{args.host} 'mkdir -p ~{REMOTE_USER}/.ai-token-analyzer'")
    run_cmd(f"ssh root@{args.host} 'cp /tmp/config.json ~{REMOTE_USER}/.ai-token-analyzer/config.json'")
    run_cmd(f"ssh root@{args.host} 'chown {REMOTE_USER}:{REMOTE_USER} ~{REMOTE_USER}/.ai-token-analyzer/config.json'")
    run_cmd(f"ssh root@{args.host} 'rm /tmp/config.json'")
    os.unlink(temp_config)
    print("✓ Configuration created\n")

    # Step 6: Set up upload service
    if not args.no_setup_service:
        print("5. Setting up upload service...")
        service_content = f'''[Unit]
Description=AI Token Analyzer - Upload Service
After=network.target

[Service]
Type=simple
Restart=always
RestartSec=5
User={args.user}
Group={args.user}
WorkingDirectory=/opt/ai-token-analyzer
Environment="PYTHONUNBUFFERED=1"
Environment="UPLOAD_SERVER={args.server_url}"
Environment="UPLOAD_AUTH_KEY={args.auth_key}"
Environment="UPLOAD_HOSTNAME={args.hostname}"
ExecStart=/usr/bin/python3 /opt/ai-token-analyzer/scripts/upload_to_server.py \\
    --server $UPLOAD_SERVER \\
    --auth-key $UPLOAD_AUTH_KEY \\
    --hostname $UPLOAD_HOSTNAME \\
    --daemon \\
    --interval 30 \\
    --incremental
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ai-token-upload

[Install]
WantedBy=multi-user.target
'''

        # Write service file locally then copy
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.service', delete=False) as f:
            f.write(service_content)
            service_file = f.name

        run_cmd(f"scp {service_file} root@{args.host}:/tmp/ai-token-upload.service")
        run_cmd(f"ssh root@{args.host} 'cp /tmp/ai-token-upload.service /etc/systemd/system/'")
        run_cmd(f"ssh root@{args.host} 'rm /tmp/ai-token-upload.service'")
        os.unlink(service_file)

        # Reload systemd
        run_cmd(f"ssh root@{args.host} 'systemctl daemon-reload'")
        run_cmd(f"ssh root@{args.host} 'systemctl enable ai-token-upload'")

        if not args.no_start:
            print("  Starting service...")
            run_cmd(f"ssh root@{args.host} 'systemctl start ai-token-upload'")

        print("✓ Upload service set up\n")

    # Step 7: Verify installation
    print("6. Verifying installation...")
    result = run_cmd(f"ssh root@{args.host} 'systemctl status ai-token-upload --no-pager'")
    if result.returncode == 0:
        print("\n✓ Installation successful!")
    else:
        print("\n⚠ Installation completed but service check failed")

    print(f"\n=== Deployment Summary ===")
    print(f"Host: {args.hostname} ({args.host})")
    print(f"Server: {args.server_url}")
    print(f"Upload interval: 30 seconds")
    print(f"\nTo check logs: ssh root@{args.host} 'journalctl -u ai-token-upload -f'")


if __name__ == '__main__':
    main()
