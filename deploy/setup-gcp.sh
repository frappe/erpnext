#!/bin/bash
# ZirakERP — Google Cloud VM Setup Script
# Run this on a fresh Ubuntu 22.04 e2-micro instance
set -e

echo "=== ZirakERP GCP Deployment ==="

# 1. Create 4GB swap (critical for 1GB RAM VM)
echo ">>> Setting up 4GB swap..."
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
sudo sysctl vm.swappiness=60

# 2. Install Docker
echo ">>> Installing Docker..."
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 3. Add current user to docker group
sudo usermod -aG docker $USER

# 4. Clone the repo (replace with your actual repo URL)
echo ">>> Cloning ZirakERP..."
cd ~
git clone https://github.com/AlanJumeworworworworworw/zirakerp.git
cd zirakerp

# 5. Build and start
echo ">>> Building ZirakERP Docker image..."
docker compose -f docker/docker-compose.yml build

echo ">>> Starting ZirakERP..."
docker compose -f docker/docker-compose.yml up -d

echo ""
echo "=== ZirakERP is starting! ==="
echo "It takes 2-3 minutes for the database and site to initialize."
echo "Check progress with: docker compose -f docker/docker-compose.yml logs create-site -f"
echo ""
echo "Once ready, access at: http://$(curl -s ifconfig.me):8080"
echo "Login: Administrator / admin"
