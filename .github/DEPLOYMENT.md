Deploy to EC2 - notes
=====================

This repository includes a GitHub Actions workflow `.github/workflows/deploy-ec2.yml` that packages the repo and deploys to an EC2 host using SSH.

Required repository secrets (add via GitHub -> Settings -> Secrets):
- `EC2_HOST` - public IP or DNS of the EC2 instance
- `EC2_USER` - username for SSH (e.g., `ubuntu` or `ec2-user`)
- `EC2_SSH_KEY` - private SSH key (PEM) content for the `EC2_USER`
- `EC2_SSH_PORT` - optional SSH port (default 22)
- `REMOTE_APP_DIR` - optional path on server to deploy (default `/opt/erpnext`)

Server-side setup (suggested):
1. Copy the `deploy/deploy_ec2.sh` script to `/usr/local/bin/deploy_erpnext.sh` on the EC2 host and make it executable:

   sudo mkdir -p /usr/local/bin
   sudo cp deploy/deploy_ec2.sh /usr/local/bin/deploy_erpnext.sh
   sudo chmod +x /usr/local/bin/deploy_erpnext.sh

2. Ensure `rsync`, `tar`, `python3`, and `pip` are installed on the server.

3. (Optional) Create a `systemd` unit named `erpnext.service` that starts your application (gunicorn/uvicorn, nginx, supervisor, etc.) and ensure it can be restarted by the deploy script.

Notes:
- The workflow uses the `EC2_SSH_KEY` secret and `scp`/`ssh` to upload the artifact and run the server-side helper script.
- Adjust `deploy/deploy_ec2.sh` to fit your production process (migrations, virtualenv activation, database migrations, worker restarts, etc.).
