# 🚀 EC2 배포 전략 및 가이드

이 문서는 FastAPI 백엔드를 **Docker 없이 EC2에 직접 배포**하는 전체 전략과 실행 방법을 설명합니다.

---

## 📍 배포 위치 전략

### **권장 위치: `/opt/langchain`** ⭐

**선택 이유:**
- ✅ `/opt/`는 선택적 소프트웨어 패키지를 위한 **Linux 표준 위치** (FHS - Filesystem Hierarchy Standard)
- ✅ 시스템 패키지와 분리되어 관리가 용이
- ✅ 권한 관리가 명확 (`sudo` 필요, 프로덕션에 적합)
- ✅ systemd 서비스 파일과 호환
- ✅ GitHub Actions 워크플로우와 일치

**대안 위치 (권장하지 않음):**
- `/home/ubuntu/langchain`: 개발/테스트용, 프로덕션 부적합
- `/srv/langchain`: 서비스 데이터용이지만 덜 일반적
- `/var/www/langchain`: 주로 정적 파일용

---

## 🏗️ 배포 아키텍처

### 전체 구조

```
┌─────────────────┐
│  GitHub Repo    │
│  (main branch)  │
└────────┬────────┘
         │
         │ git push
         ▼
┌─────────────────┐
│ GitHub Actions  │
│  (CI/CD)        │
│  - 테스트       │
│  - SSH 배포     │
└────────┬────────┘
         │
         │ SSH
         ▼
┌─────────────────┐
│  EC2 Instance   │
│  /opt/langchain │
│                 │
│  ┌───────────┐ │
│  │ Python    │ │
│  │ venv      │ │
│  └───────────┘ │
│  ┌───────────┐ │
│  │ systemd   │ │
│  │ service   │ │
│  └───────────┘ │
│  ┌───────────┐ │
│  │ PostgreSQL│ │
│  └───────────┘ │
└─────────────────┘
```

### 기술 스택

- **서버**: EC2 (CPU 전용, t3.xlarge 이상 권장)
- **OS**: Ubuntu 22.04 LTS
- **Python**: 3.11 (가상환경)
- **데이터베이스**: PostgreSQL + pgvector (시스템 설치)
- **프로세스 관리**: systemd
- **CI/CD**: GitHub Actions
- **배포 방식**: Docker 없이 직접 배포

---

## 🎯 1단계: EC2 인스턴스 준비

### A. EC2 인스턴스 생성

**AWS Console에서 설정:**
- **인스턴스 타입**: t3.xlarge 이상 (CPU 전용)
- **OS**: Ubuntu 22.04 LTS
- **스토리지**: 50GB 이상 (모델 파일 포함 시 100GB 권장)
- **보안 그룹**:
  - SSH (22)
  - HTTP (80)
  - HTTPS (443)
  - Custom TCP (8000) - FastAPI 포트

### B. EC2 초기 설정

**방법 1: 자동 설정 스크립트** ⭐ 권장

```bash
# EC2에 SSH 접속 후
curl -o /tmp/setup_ec2_direct.sh https://raw.githubusercontent.com/your-org/langchain/main/scripts/setup_ec2_direct.sh
chmod +x /tmp/setup_ec2_direct.sh
bash /tmp/setup_ec2_direct.sh
```

**방법 2: 수동 설정**

```bash
# 1. 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 2. 필수 패키지 설치
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

# 3. PostgreSQL 설정
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 4. PostgreSQL 사용자 및 데이터베이스 생성
sudo -u postgres psql << EOF
CREATE USER langchain WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE langchain OWNER langchain;
\c langchain
CREATE EXTENSION IF NOT EXISTS vector;
\q
EOF

# 5. 애플리케이션 디렉토리 생성
sudo mkdir -p /opt/langchain
sudo chown ubuntu:ubuntu /opt/langchain
cd /opt/langchain

# 6. Git 저장소 clone
git clone https://github.com/your-org/langchain.git .

# 7. Python 가상환경 생성
python3.11 -m venv venv
source venv/bin/activate

# 8. 의존성 설치
pip install --upgrade pip
pip install -r app/requirements.txt
```

### C. `.env` 파일 생성

```bash
nano /opt/langchain/.env
```

```env
# PostgreSQL
POSTGRES_USER=langchain
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=langchain
DATABASE_URL=postgresql://langchain:your_secure_password_here@localhost:5432/langchain

# QLoRA 설정 (CPU 모드)
USE_QLORA=1
QLORA_BASE_MODEL_PATH=/opt/langchain/app/model/midm
LLM_PROVIDER=huggingface
PYTHONUNBUFFERED=1

# CPU 전용 (CUDA 비활성화)
CUDA_VISIBLE_DEVICES=
```

### D. systemd 서비스 설정

```bash
sudo nano /etc/systemd/system/langchain-backend.service
```

다음 내용 입력:

```ini
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
```

서비스 활성화 및 시작:

```bash
sudo systemctl daemon-reload
sudo systemctl enable langchain-backend
sudo systemctl start langchain-backend

# 상태 확인
sudo systemctl status langchain-backend
```

### E. 모델 파일 업로드 (필요 시)

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

#### 1. `EC2_SSH_PRIVATE_KEY`

**로컬에서 SSH 키 생성:**
```bash
ssh-keygen -t ed25519 -C "github-actions@langchain" -f ~/.ssh/langchain_deploy
```

**Private Key 복사 (GitHub Secret에 등록):**
```bash
cat ~/.ssh/langchain_deploy
# 전체 내용 복사 (BEGIN~END 포함)
```

**Public Key를 EC2에 등록:**
```bash
# EC2에서 실행
echo "ssh-ed25519 AAAAC3Nza... github-actions@langchain" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

#### 2. `EC2_HOST`
```
54.180.83.177  # EC2 Public IP 또는 도메인
```

#### 3. `EC2_USER`
```
ubuntu  # 또는 ec2-user (Amazon Linux의 경우)
```

#### 4. `DEPLOY_PATH`
```
/opt/langchain
```

---

## 🎯 3단계: 배포 실행

### **방법 1: 자동 배포 (GitHub Actions)** ⭐ 권장

```bash
# 코드 변경 후 main 브랜치에 push
git add .
git commit -m "feat: add new feature"
git push origin main

# 자동으로 GitHub Actions 실행됨
# GitHub 저장소 → Actions 탭에서 진행 상황 확인
```

**배포 프로세스:**
1. 테스트 실행 (pytest)
2. 테스트 통과 시 SSH로 EC2 접속
3. `/opt/langchain`에서 `git pull`
4. Python 가상환경 의존성 업데이트
5. systemd 서비스 재시작
6. 헬스체크 (API 응답 확인)

### **방법 2: 수동 배포 (GitHub Actions)**

1. GitHub 저장소 → **Actions** 탭
2. **Deploy to EC2** 워크플로우 선택
3. **Run workflow** → **Run workflow** 버튼 클릭
4. 필요 시 `git_ref` 및 `skip_tests` 옵션 설정

### **방법 3: 로컬에서 직접 배포**

```bash
# 로컬 터미널에서 실행 (Windows는 Git Bash 사용)
EC2_HOST=54.180.83.177 \
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
- ✅ "Deployment completed successfully!" 메시지 확인

### B. EC2에서 직접 확인

```bash
# SSH 접속
ssh -i ~/.ssh/langchain_deploy ubuntu@54.180.83.177

# systemd 서비스 상태 확인
sudo systemctl status langchain-backend

# 백엔드 로그 확인 (실시간)
sudo journalctl -u langchain-backend -f

# 최근 100줄 로그 확인
sudo journalctl -u langchain-backend -n 100

# API 응답 확인
curl http://localhost:8000/docs
```

### C. 브라우저에서 확인

```
http://your-ec2-ip:8000/docs  # FastAPI Swagger UI
```

---

## 🚨 트러블슈팅

### 1. "Permission denied (publickey)" 에러

```bash
# EC2에서 확인
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
cat ~/.ssh/authorized_keys  # Public Key 확인

# GitHub Secret의 Private Key가 올바른지 확인 (BEGIN~END 포함)
```

### 2. systemd 서비스가 시작되지 않음

```bash
# 서비스 상태 확인
sudo systemctl status langchain-backend

# 상세 로그 확인
sudo journalctl -u langchain-backend -n 100

# .env 파일 확인
cat /opt/langchain/.env

# Python 경로 확인
which python
/opt/langchain/venv/bin/python --version

# 수동 재시작
sudo systemctl restart langchain-backend
```

### 3. API가 응답하지 않음

```bash
# 포트 확인
sudo netstat -tuln | grep 8000

# 방화벽 확인 (EC2 보안 그룹에서 8000 포트 오픈되어 있는지)

# 프로세스 확인
ps aux | grep python

# 서비스 재시작
sudo systemctl restart langchain-backend
```

### 4. 모델 로딩 실패

```bash
# 모델 파일 확인
ls -lh /opt/langchain/app/model/midm

# 환경 변수 확인
cat /opt/langchain/.env | grep QLORA

# 로그에서 에러 확인
sudo journalctl -u langchain-backend | grep -i "model\|error"
```

### 5. PostgreSQL 연결 실패

```bash
# PostgreSQL 상태 확인
sudo systemctl status postgresql

# PostgreSQL 연결 테스트
sudo -u postgres psql -c "SELECT version();"

# 데이터베이스 확인
sudo -u postgres psql -c "\l" | grep langchain

# 연결 문자열 확인
cat /opt/langchain/.env | grep DATABASE_URL
```

---

## 🔄 롤백 방법

### A. Git 커밋 롤백

```bash
# EC2에서 실행
cd /opt/langchain
git log --oneline  # 이전 커밋 확인
git reset --hard <commit-hash>
source venv/bin/activate
pip install -r app/requirements.txt
sudo systemctl restart langchain-backend
```

### B. 이전 버전으로 체크아웃

```bash
cd /opt/langchain
git checkout <tag-or-branch>
source venv/bin/activate
pip install -r app/requirements.txt
sudo systemctl restart langchain-backend
```

---

## 📊 배포 프로세스 흐름도

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
│ Send Alert   │              │ pip install  │
└──────────────┘              │ systemctl    │
                              │ restart      │
                              └──────┬───────┘
                                     │
                                     ▼
                              ┌──────────────┐
                              │ Health Check │
                              │ API Ready ✅ │
                              └──────────────┘
```

---

## ✅ 배포 체크리스트

### 사전 준비
- [ ] EC2 인스턴스 생성 (t3.xlarge 이상, Ubuntu 22.04)
- [ ] Python 3.11, PostgreSQL 설치 완료
- [ ] `/opt/langchain` 디렉토리 생성 및 권한 설정
- [ ] Git 저장소 clone 완료
- [ ] Python 가상환경 생성 및 의존성 설치
- [ ] `.env` 파일 생성 (CPU 전용 설정)
- [ ] 모델 파일 업로드 (필요 시)
- [ ] systemd 서비스 파일 생성 및 활성화

### GitHub Secrets 설정
- [ ] `EC2_SSH_PRIVATE_KEY` 등록 (BEGIN~END 포함)
- [ ] `EC2_HOST` 등록 (EC2 Public IP)
- [ ] `EC2_USER` 등록 (`ubuntu`)
- [ ] `DEPLOY_PATH` 등록 (`/opt/langchain`)

### 배포 실행
- [ ] GitHub Actions 워크플로우 실행 확인
- [ ] 테스트 통과 확인
- [ ] 배포 성공 확인 (✅ Deployment completed successfully!)

### 배포 후 확인
- [ ] `sudo systemctl status langchain-backend`로 서비스 실행 확인
- [ ] `sudo journalctl -u langchain-backend -f`로 로그 확인
- [ ] `curl http://localhost:8000/docs`로 API 응답 확인
- [ ] 브라우저에서 `http://your-ec2-ip:8000/docs` 접속 확인

---

## 📝 핵심 전략 요약

1. **배포 위치**: `/opt/langchain` (Linux 표준, 프로덕션 적합)
2. **배포 방식**: Docker 없이 직접 배포 (Python 가상환경 + systemd)
3. **CI/CD**: GitHub Actions 자동 배포
4. **프로세스 관리**: systemd 서비스 (자동 재시작, 로그 관리)
5. **데이터베이스**: PostgreSQL 시스템 설치 (Docker 없음)
6. **환경 설정**: `.env` 파일로 관리
7. **모니터링**: `journalctl`로 로그 확인

---

## 🤝 도움이 필요하신가요?

- GitHub Issues: 버그 리포트 및 기능 제안
- 팀 채널: 긴급 문제 및 질문
