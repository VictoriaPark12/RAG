# 🚀 EC2 배포 가이드 (빠른 시작)

이 문서는 FastAPI 백엔드를 EC2에 GitHub Actions를 통해 자동 배포하는 방법을 간단히 설명합니다.

---

## 📌 배포 방법 (3가지)

### 1️⃣ **자동 배포 (GitHub Actions)** ⭐ 권장
- `main` 브랜치에 push하면 자동으로 EC2에 배포
- 테스트 → 빌드 → 배포가 자동으로 진행

### 2️⃣ **수동 배포 (GitHub Actions)**
- GitHub 웹사이트에서 버튼 클릭으로 배포
- 테스트 건너뛰고 바로 배포 가능

### 3️⃣ **로컬에서 직접 배포 (스크립트)**
- 로컬 터미널에서 스크립트 실행
- GitHub Actions 없이 SSH로 직접 배포

---

## 🎯 1단계: EC2 인스턴스 준비

### A. EC2 인스턴스 생성
```bash
# AWS Console에서 EC2 인스턴스 생성
# - 타입: g4dn.xlarge (GPU) 또는 t3.xlarge (CPU)
# - OS: Ubuntu 22.04 LTS
# - 스토리지: 50GB 이상
# - 보안 그룹: SSH(22), HTTP(80), HTTPS(443), Custom(8000) 오픈
```

### B. EC2 초기 설정 (SSH 접속 후)
```bash
# Docker 설치
sudo apt update && sudo apt upgrade -y
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# GPU 사용 시 (선택사항)
sudo apt install -y nvidia-driver-535
sudo reboot
# nvidia-docker2 설치 (재부팅 후)
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt update && sudo apt install -y nvidia-docker2
sudo systemctl restart docker
```

### C. 애플리케이션 디렉토리 생성
```bash
sudo mkdir -p /opt/langchain
sudo chown ubuntu:ubuntu /opt/langchain
cd /opt/langchain

# Git 저장소 clone
git clone https://github.com/your-org/langchain.git .
```

### D. `.env` 파일 생성
```bash
nano /opt/langchain/.env
```

```env
# PostgreSQL
POSTGRES_USER=langchain
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=langchain
DATABASE_URL=postgresql://langchain:your_secure_password_here@postgres:5432/langchain

# QLoRA 설정
USE_QLORA=1
QLORA_BASE_MODEL_PATH=/app/model/midm
LLM_PROVIDER=huggingface
PYTHONUNBUFFERED=1

# GPU 사용 시
CUDA_VISIBLE_DEVICES=0
```

### E. 모델 파일 업로드
```bash
# 방법 1: SCP (로컬에서 실행)
scp -i your-key.pem -r app/model/midm ubuntu@your-ec2-ip:/opt/langchain/app/model/

# 방법 2: S3 (EC2에서 실행)
aws s3 sync s3://your-bucket/models/midm /opt/langchain/app/model/midm
```

---

## 🎯 2단계: GitHub Secrets 설정

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions**

### 필수 Secrets (4개)

1. **`EC2_SSH_PRIVATE_KEY`**
   ```bash
   # 로컬에서 SSH 키 생성
   ssh-keygen -t ed25519 -C "github-actions@langchain" -f ~/.ssh/langchain_deploy

   # Private Key 복사 (GitHub Secret에 등록)
   cat ~/.ssh/langchain_deploy

   # Public Key 복사 (EC2에 등록)
   cat ~/.ssh/langchain_deploy.pub
   ```

   EC2에 Public Key 등록:
   ```bash
   # EC2에서 실행
   echo "ssh-ed25519 AAAAC3Nza... github-actions@langchain" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

2. **`EC2_HOST`**
   ```
   54.123.45.67  # EC2 Public IP 또는 도메인
   ```

3. **`EC2_USER`**
   ```
   ubuntu  # 또는 ec2-user (Amazon Linux의 경우)
   ```

4. **`DEPLOY_PATH`**
   ```
   /opt/langchain
   ```

---

## 🎯 3단계: 배포 실행

### **방법 1: 자동 배포 (권장)**
```bash
# 코드 변경 후 main 브랜치에 push
git add .
git commit -m "feat: add new feature"
git push origin main

# 자동으로 GitHub Actions 실행됨
# GitHub 저장소 → Actions 탭에서 진행 상황 확인
```

### **방법 2: 수동 배포 (GitHub Actions)**
1. GitHub 저장소 → **Actions** 탭
2. **Manual Deploy to EC2** 워크플로우 선택
3. **Run workflow** → **Run workflow** 버튼 클릭

### **방법 3: 로컬에서 직접 배포**
```bash
# 로컬 터미널에서 실행 (Windows는 Git Bash 사용)
EC2_HOST=54.123.45.67 \
EC2_USER=ubuntu \
SSH_KEY_PATH=~/.ssh/langchain_deploy \
./scripts/deploy_to_ec2.sh
```

---

## 🎯 4단계: 배포 확인

### A. GitHub Actions 로그 확인
- GitHub 저장소 → **Actions** 탭
- 최근 워크플로우 실행 클릭
- 각 step별 로그 확인

### B. EC2에서 직접 확인
```bash
# SSH 접속
ssh -i ~/.ssh/langchain_deploy ubuntu@54.123.45.67

# Docker 컨테이너 상태 확인
docker ps

# 백엔드 로그 확인
docker logs -f langchain-backend

# API 응답 확인
curl http://localhost:8000/docs
```

### C. 브라우저에서 확인
```
http://your-ec2-ip:8000/docs  # FastAPI Swagger UI
```

---

## 📊 배포 프로세스 흐름

```
┌──────────────┐
│ Git Push     │
│ (main)       │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ GitHub       │
│ Actions      │
│ Triggered    │
└──────┬───────┘
       │
       ▼
┌──────────────┐     PASS     ┌──────────────┐
│ Run Tests    │─────────────▶│ SSH Deploy   │
│ (pytest)     │              │ to EC2       │
└──────┬───────┘              └──────┬───────┘
       │ FAIL                        │
       ▼                             ▼
┌──────────────┐              ┌──────────────┐
│ Stop Deploy  │              │ git pull     │
│ Send Alert   │              │ docker build │
└──────────────┘              │ restart      │
                              └──────┬───────┘
                                     │
                                     ▼
                              ┌──────────────┐
                              │ Health Check │
                              │ API Ready ✅ │
                              └──────────────┘
```

---

## 🚨 트러블슈팅

### 1. "Permission denied (publickey)" 에러
```bash
# EC2에서 확인
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/authorized_keys  # Public Key 확인
```

### 2. Docker 컨테이너가 시작되지 않음
```bash
# EC2에서 로그 확인
docker logs langchain-backend
docker logs langchain-postgres

# .env 파일 확인
cat /opt/langchain/.env

# 수동 재시작
cd /opt/langchain
docker-compose down
docker-compose up -d
```

### 3. API가 응답하지 않음
```bash
# 포트 확인
netstat -tuln | grep 8000

# 방화벽 확인 (EC2 보안 그룹에서 8000 포트 오픈되어 있는지)

# 컨테이너 내부에서 확인
docker exec -it langchain-backend curl http://localhost:8000/docs
```

### 4. 모델 로딩 실패
```bash
# 모델 파일 확인
ls -lh /opt/langchain/app/model/midm

# 환경 변수 확인
docker exec -it langchain-backend env | grep QLORA

# 로그에서 에러 확인
docker logs langchain-backend | grep -i "model\|error"
```

---

## 🔄 롤백 방법

### A. Git 커밋 롤백
```bash
# EC2에서 실행
cd /opt/langchain
git log --oneline  # 이전 커밋 확인
git reset --hard <commit-hash>
docker-compose up -d --build
```

### B. 백업 태그 사용
```bash
# 배포 시 자동으로 생성된 백업 태그 확인
git tag | grep backup

# 백업 태그로 복원
git checkout backup-20250118-153000
docker-compose up -d --build
```

---

## 📚 상세 문서

- [EC2_SETUP.md](docs/EC2_SETUP.md) - EC2 상세 설정 가이드
- [GITHUB_SECRETS_SETUP.md](docs/GITHUB_SECRETS_SETUP.md) - GitHub Secrets 상세 가이드
- [DEPLOYMENT_STRATEGY.md](docs/DEPLOYMENT_STRATEGY.md) - 배포 전략 전체 문서

---

## 🎯 배포 체크리스트

### 사전 준비
- [ ] EC2 인스턴스 생성 및 초기 설정 완료
- [ ] Docker + Docker Compose 설치 완료
- [ ] Git 저장소 clone 완료 (`/opt/langchain`)
- [ ] `.env` 파일 생성 완료
- [ ] 모델 파일 업로드 완료 (`/opt/langchain/app/model/midm`)

### GitHub Secrets 설정
- [ ] `EC2_SSH_PRIVATE_KEY` 등록
- [ ] `EC2_HOST` 등록 (EC2 Public IP)
- [ ] `EC2_USER` 등록 (ubuntu 또는 ec2-user)
- [ ] `DEPLOY_PATH` 등록 (/opt/langchain)

### 배포 실행
- [ ] GitHub Actions 워크플로우 실행 확인
- [ ] 테스트 통과 확인
- [ ] 배포 성공 확인 (✅ Deployment completed successfully!)

### 배포 후 확인
- [ ] `docker ps`로 컨테이너 실행 확인
- [ ] `docker logs -f langchain-backend`로 로그 확인
- [ ] `curl http://localhost:8000/docs`로 API 응답 확인
- [ ] 브라우저에서 `http://your-ec2-ip:8000/docs` 접속 확인

---

## 🤝 도움이 필요하신가요?

- GitHub Issues: 버그 리포트 및 기능 제안
- 팀 채널: 긴급 문제 및 질문
- 문서: `docs/` 폴더의 상세 가이드 참고

