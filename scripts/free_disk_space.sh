#!/bin/bash
# EC2 인스턴스에서 디스크 공간을 확보하는 스크립트
# EC2에 SSH 접속 후 실행하거나, deploy_to_ec2.sh에서 호출 가능

set -e

echo "🧹 Starting disk space cleanup..."

# 현재 디스크 사용률 확인
echo "💾 Current disk usage:"
df -h /

# apt 캐시 정리
echo "🧹 Cleaning apt cache..."
sudo apt clean
sudo apt autoclean

# 패키지 목록 캐시 정리
echo "🧹 Cleaning package lists..."
sudo rm -rf /var/lib/apt/lists/*
sudo mkdir -p /var/lib/apt/lists/partial

# 임시 파일 정리
echo "🧹 Cleaning temporary files..."
sudo rm -rf /tmp/* /var/tmp/* 2>/dev/null || true

# 오래된 로그 파일 정리
echo "🧹 Cleaning old log files..."
sudo journalctl --vacuum-time=3d 2>/dev/null || true
sudo find /var/log -type f -name "*.log" -mtime +7 -delete 2>/dev/null || true
sudo find /var/log -type f -name "*.gz" -delete 2>/dev/null || true

# 오래된 백업 파일 정리 (7일 이상 된 백업)
if [ -d "/opt/langchain" ]; then
  echo "🧹 Cleaning old backups in /opt/langchain..."
  find /opt/langchain -name "backup-*" -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true
fi

# 사용하지 않는 패키지 제거
echo "🧹 Removing unused packages..."
sudo apt autoremove -y 2>/dev/null || true

# Docker가 설치되어 있다면 정리
if command -v docker &> /dev/null; then
  echo "🧹 Cleaning Docker..."
  sudo docker system prune -af --volumes 2>/dev/null || true
fi

# 최종 디스크 사용률 확인
echo "💾 Disk usage after cleanup:"
df -h /

DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
echo "✅ Cleanup completed. Disk usage: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -gt 90 ]; then
  echo "⚠️  WARNING: Disk usage is still high (${DISK_USAGE}%)"
  echo "Consider:"
  echo "  1. Increasing EC2 instance storage size"
  echo "  2. Removing large files manually"
  echo "  3. Moving data to external storage"
fi

