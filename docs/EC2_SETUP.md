# EC2 인스턴스 설정 가이드

## 1. EC2 인스턴스 생성

### 권장 사양
- **인스턴스 타입**: `g4dn.xlarge` 이상 (GPU 필요, QLoRA 사용)
  - 또는 CPU만 사용할 경우: `t3.xlarge` (4 vCPU, 16GB RAM)
- **OS**: Ubuntu 22.04 LTS (또는 Amazon Linux 2023)
- **스토리지**: 50GB 이상 (모델 파일 크기 고려)
- **보안 그룹**:
  - SSH (22): 본인 IP만
  - HTTP (80): 0.0.0.0/0
  - HTTPS (443): 0.0.0.0/0
  - Custom TCP (8000): 0.0.0.0/0 (또는 프론트엔드 IP만)

## 2. EC2 초기 설정 (SSH 접속 후)

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# Docker 설치
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu  # 또는 ec2-user

# NVIDIA Driver 설치 (GPU 인스턴스만)
sudo apt install -y nvidia-driver-535
sudo reboot  # 재부팅 필요

# NVIDIA Container Toolkit 설치 (GPU 인스턴스만)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update
sudo apt install -y nvidia-docker2
sudo systemctl restart docker

# 확인
docker --version
docker-compose --version
nvidia-smi  # GPU 인스턴스만
```

## 3. 애플리케이션 디렉토리 생성

```bash
sudo mkdir -p /opt/langchain
sudo chown ubuntu:ubuntu /opt/langchain  # 또는 ec2-user
cd /opt/langchain
```

## 4. 환경 변수 설정

```bash
# /opt/langchain/.env 파일 생성
sudo nano /opt/langchain/.env
```

필수 환경 변수:
```env
# Database
POSTGRES_USER=langchain
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=langchain
DATABASE_URL=postgresql://langchain:your_secure_password_here@postgres:5432/langchain

# QLoRA 설정
USE_QLORA=1
QLORA_BASE_MODEL_PATH=/app/model/midm
QLORA_ADAPTER_PATH=/app/model/midm-adapter  # 선택사항
LLM_PROVIDER=huggingface  # 또는 ollama

# FastAPI
PYTHONUNBUFFERED=1
CUDA_VISIBLE_DEVICES=0  # GPU 사용 시

# 선택사항
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
```

## 5. GitHub Actions 배포 유저 설정

```bash
# GitHub Actions에서 사용할 SSH 키 등록
mkdir -p ~/.ssh
nano ~/.ssh/authorized_keys  # GitHub Secrets에 저장할 PUBLIC KEY를 여기 추가
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## 6. 모델 파일 업로드

**방법 1: SCP로 직접 업로드**
```bash
# 로컬에서 실행
scp -i your-key.pem -r app/model/midm ubuntu@your-ec2-ip:/opt/langchain/app/model/
```

**방법 2: S3 사용 (권장)**
```bash
# EC2에서 실행
aws s3 sync s3://your-bucket/models/midm /opt/langchain/app/model/midm
```

**방법 3: Hugging Face Hub**
```python
# app/service/chat_service.py에서 자동 다운로드
from huggingface_hub import snapshot_download
model_path = snapshot_download(repo_id="your-org/midm", cache_dir="/opt/langchain/app/model")
```

## 7. 방화벽 설정 (선택사항)

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 8000/tcp # FastAPI (또는 nginx 뒤에 숨길 경우 불필요)
sudo ufw enable
```

## 8. 로그 확인

```bash
# Docker 로그
docker logs -f langchain-backend
docker logs -f langchain-postgres

# 시스템 로그
journalctl -u docker -f
```

## 9. 자동 재시작 설정

```bash
# Docker Compose 서비스 자동 시작
sudo nano /etc/systemd/system/langchain.service
```

```ini
[Unit]
Description=LangChain FastAPI Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/langchain
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
User=ubuntu

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable langchain.service
sudo systemctl start langchain.service
```

