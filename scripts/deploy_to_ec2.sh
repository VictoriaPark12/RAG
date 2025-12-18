#!/bin/bash

# 로컬에서 EC2로 직접 배포하는 스크립트 (GitHub Actions 없이 사용 가능)

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 환경 변수 확인
if [ -z "$EC2_HOST" ] || [ -z "$EC2_USER" ] || [ -z "$SSH_KEY_PATH" ]; then
  echo -e "${RED}❌ ERROR: Required environment variables not set${NC}"
  echo "Usage: EC2_HOST=54.123.45.67 EC2_USER=ubuntu SSH_KEY_PATH=~/.ssh/langchain_deploy.pem ./scripts/deploy_to_ec2.sh"
  exit 1
fi

DEPLOY_PATH="${DEPLOY_PATH:-/opt/langchain}"

echo -e "${GREEN}🚀 Starting deployment to EC2...${NC}"
echo "Host: $EC2_HOST"
echo "User: $EC2_USER"
echo "Deploy Path: $DEPLOY_PATH"

# SSH 연결 테스트
echo -e "${YELLOW}🔍 Testing SSH connection...${NC}"
if ! ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=10 "$EC2_USER@$EC2_HOST" "echo 'SSH OK'"; then
  echo -e "${RED}❌ SSH connection failed${NC}"
  exit 1
fi

# 배포 실행
echo -e "${YELLOW}📦 Deploying to EC2...${NC}"
ssh -i "$SSH_KEY_PATH" "$EC2_USER@$EC2_HOST" << ENDSSH
  set -e

  echo "📂 Navigating to deploy directory..."
  cd $DEPLOY_PATH

  # 백업 생성
  BACKUP_TAG="backup-\$(date +%Y%m%d-%H%M%S)"
  echo "💾 Creating backup: \$BACKUP_TAG"
  git tag \$BACKUP_TAG 2>/dev/null || true

  # 최신 코드 pull
  echo "🔄 Pulling latest changes..."
  git fetch origin main
  git reset --hard origin/main

  # .env 확인
  if [ ! -f .env ]; then
    echo "❌ ERROR: .env file not found!"
    exit 1
  fi

  # Docker 빌드
  echo "🔨 Building Docker images..."
  docker-compose build --no-cache backend

  # 서비스 재시작
  echo "♻️  Restarting services..."
  docker-compose down
  docker-compose up -d

  # 헬스체크
  echo "⏳ Waiting for services to start..."
  sleep 10

  # 백엔드 상태 확인
  if docker ps | grep -q langchain-backend; then
    echo "✅ Backend is running"
  else
    echo "❌ Backend failed to start"
    docker logs --tail 50 langchain-backend
    exit 1
  fi

  # API 헬스체크
  echo "🔍 Checking API health..."
  for i in {1..30}; do
    if curl -f http://localhost:8000/docs > /dev/null 2>&1; then
      echo "✅ API is healthy!"
      break
    fi
    if [ \$i -eq 30 ]; then
      echo "❌ API health check failed"
      docker logs --tail 50 langchain-backend
      exit 1
    fi
    echo "⏳ Waiting for API... (\$i/30)"
    sleep 2
  done

  echo "🎉 Deployment completed successfully!"
ENDSSH

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✅ Deployment succeeded${NC}"
  echo -e "${GREEN}🌐 Access your API at: http://$EC2_HOST:8000/docs${NC}"
else
  echo -e "${RED}❌ Deployment failed${NC}"
  exit 1
fi

