#!/bin/bash
# EC2 직접 배포 초기 설정 스크립트 (Docker 없음)
# EC2 인스턴스에서 한 번만 실행

set -e

echo "🚀 Setting up EC2 for direct deployment (no Docker)..."

# 시스템 업데이트
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
echo "📦 Installing required packages..."
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    git \
    curl \
    build-essential \
    libpq-dev

# PostgreSQL 설정
echo "🗄️ Configuring PostgreSQL..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

# PostgreSQL 사용자 및 데이터베이스 생성
echo "🗄️ Creating PostgreSQL user and database..."
sudo -u postgres psql << EOF
CREATE USER langchain WITH PASSWORD 'changeme_secure_password_here';
CREATE DATABASE langchain OWNER langchain;
\c langchain
CREATE EXTENSION IF NOT EXISTS vector;
\q
EOF

# 애플리케이션 디렉토리 생성
echo "📁 Creating application directory..."
sudo mkdir -p /opt/langchain
sudo chown ubuntu:ubuntu /opt/langchain

# Git 저장소 clone (이미 존재하면 스킵)
if [ ! -d /opt/langchain/.git ]; then
    echo "📥 Cloning repository..."
    cd /opt/langchain
    git clone https://github.com/your-org/langchain.git .
else
    echo "✅ Repository already exists, skipping clone..."
fi

# Python 가상환경 생성
echo "🐍 Creating Python virtual environment..."
cd /opt/langchain
python3.11 -m venv venv
source venv/bin/activate

# pip 업그레이드 및 의존성 설치
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r app/requirements.txt

# .env 파일 생성 (템플릿)
if [ ! -f /opt/langchain/.env ]; then
    echo "📝 Creating .env file template..."
    cat > /opt/langchain/.env << 'ENVEOF'
# PostgreSQL
POSTGRES_USER=langchain
POSTGRES_PASSWORD=changeme_secure_password_here
POSTGRES_DB=langchain
DATABASE_URL=postgresql://langchain:changeme_secure_password_here@localhost:5432/langchain

# QLoRA 설정 (CPU 모드)
USE_QLORA=1
QLORA_BASE_MODEL_PATH=/opt/langchain/app/model/midm
LLM_PROVIDER=huggingface
PYTHONUNBUFFERED=1

# CPU 전용 (CUDA 비활성화)
CUDA_VISIBLE_DEVICES=
ENVEOF
    echo "⚠️  Please edit /opt/langchain/.env and update the password!"
fi

# systemd 서비스 파일 생성
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/langchain-backend.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=LangChain FastAPI Backend
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/langchain/app
Environment="PATH=/opt/langchain/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/langchain/.env
ExecStart=/opt/langchain/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=langchain-backend

[Install]
WantedBy=multi-user.target
SERVICEEOF

# systemd 재로드 및 서비스 활성화
echo "⚙️ Enabling systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable langchain-backend

echo "✅ Setup completed!"
echo ""
echo "📋 Next steps:"
echo "1. Edit /opt/langchain/.env and update the PostgreSQL password"
echo "2. Upload model files to /opt/langchain/app/model/midm (if needed)"
echo "3. Start the service: sudo systemctl start langchain-backend"
echo "4. Check status: sudo systemctl status langchain-backend"
echo "5. View logs: sudo journalctl -u langchain-backend -f"

