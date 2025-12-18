# EC2 + GitHub Actions CI/CD 배포 전략

이 문서는 FastAPI 백엔드를 EC2에 GitHub Actions를 통해 자동 배포하는 전체 전략을 설명합니다.

## 📊 배포 아키텍처

```
┌─────────────┐       ┌──────────────────┐       ┌─────────────┐
│   GitHub    │──────▶│ GitHub Actions   │──────▶│   EC2       │
│ (push main) │       │ (CI/CD Pipeline) │  SSH  │ (Production)│
└─────────────┘       └──────────────────┘       └─────────────┘
                              │                          │
                              │                          ▼
                              ▼                   ┌─────────────┐
                      ┌──────────────┐            │  Docker     │
                      │ Unit Tests   │            │  Compose    │
                      │ Lint Check   │            ├─────────────┤
                      │ Build Docker │            │ FastAPI:8000│
                      └──────────────┘            │ PostgreSQL  │
                                                  │ pgvector    │
                                                  └─────────────┘
```

---

## 🎯 배포 전략 요약

| 단계 | 내용 | 도구 |
|------|------|------|
| 1️⃣ | 코드 push to `main` | Git |
| 2️⃣ | 자동 테스트 실행 | GitHub Actions + pytest |
| 3️⃣ | Docker 이미지 빌드 | Docker Buildx |
| 4️⃣ | EC2에 SSH 배포 | SSH + rsync/git pull |
| 5️⃣ | Docker Compose 재시작 | docker-compose |
| 6️⃣ | 헬스체크 확인 | curl + logs |

---

## 📋 사전 준비 (1회만)

### 1. EC2 인스턴스 설정
- [EC2_SETUP.md](./EC2_SETUP.md) 참고
- GPU 인스턴스(`g4dn.xlarge`) 또는 CPU 인스턴스(`t3.xlarge`)
- Docker + Docker Compose 설치
- NVIDIA Driver + nvidia-docker2 설치 (GPU 사용 시)

### 2. GitHub Secrets 설정
- [GITHUB_SECRETS_SETUP.md](./GITHUB_SECRETS_SETUP.md) 참고
- `EC2_SSH_PRIVATE_KEY`, `EC2_HOST`, `EC2_USER`, `DEPLOY_PATH`

### 3. EC2에 Git 저장소 clone
```bash
ssh ubuntu@your-ec2-ip
cd /opt
sudo mkdir langchain
sudo chown ubuntu:ubuntu langchain
cd langchain
git clone https://github.com/your-org/langchain.git .
```

### 4. EC2에 `.env` 파일 생성
```bash
cd /opt/langchain
nano .env
```

필수 환경 변수:
```env
POSTGRES_USER=langchain
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=langchain
DATABASE_URL=postgresql://langchain:your_secure_password@postgres:5432/langchain

USE_QLORA=1
QLORA_BASE_MODEL_PATH=/app/model/midm
LLM_PROVIDER=huggingface
PYTHONUNBUFFERED=1
```

### 5. 모델 파일 업로드
```bash
# 방법 1: SCP (로컬에서)
scp -i your-key.pem -r app/model/midm ubuntu@your-ec2-ip:/opt/langchain/app/model/

# 방법 2: S3 (EC2에서)
aws s3 sync s3://your-bucket/models/midm /opt/langchain/app/model/midm

# 방법 3: HuggingFace Hub (자동 다운로드)
# app/service/chat_service.py에서 처리
```

---

## 🚀 배포 프로세스

### GitHub Actions 워크플로우 (`.github/workflows/deploy.yml`)

#### **Step 1: 테스트 실행**
```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Set up Python 3.11
      - Install dependencies
      - Run pytest (unit tests)
```

#### **Step 2: 배포 (테스트 통과 후)**
```yaml
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - Checkout code
      - Configure SSH
      - Deploy to EC2:
          1. SSH 접속
          2. git pull origin main
          3. docker-compose build
          4. docker-compose down
          5. docker-compose up -d
          6. Health check
```

---

## 🔄 배포 흐름 상세

### 1. 개발자가 코드 push
```bash
git add .
git commit -m "feat: add new feature"
git push origin main
```

### 2. GitHub Actions 자동 트리거
- `.github/workflows/deploy.yml` 실행
- `test` job 실행 (pytest)

### 3. 테스트 통과 시 배포 시작
```bash
# EC2에서 실행되는 명령어 (SSH로 자동 실행)
cd /opt/langchain
git fetch origin main
git reset --hard origin/main

# Docker 이미지 빌드
docker-compose build --no-cache backend

# 서비스 재시작
docker-compose down
docker-compose up -d

# 헬스체크
sleep 10
curl -f http://localhost:8000/docs
```

### 4. 배포 완료 확인
- GitHub Actions 로그에서 `✅ Deployment completed successfully!` 확인
- EC2에서 `docker ps` 및 `docker logs -f langchain-backend` 확인

---

## 🛠️ 배포 옵션

### **Option 1: 자동 배포 (권장)**
- `main` 브랜치에 push 시 자동 배포
- `.github/workflows/deploy.yml` 활성화

### **Option 2: 수동 배포**
- GitHub Actions 탭에서 `workflow_dispatch` 트리거
- 또는 EC2에서 직접 `git pull && docker-compose up -d --build`

### **Option 3: Blue-Green 배포 (고급)**
```yaml
# 포트 8001에 새 버전 배포
docker-compose -f docker-compose.blue.yml up -d

# 헬스체크 통과 시 포트 전환
# nginx upstream 설정 변경 또는 ALB target group 전환

# 기존 버전(8000) 종료
docker-compose down
```

---

## 📊 모니터링 및 로그

### 실시간 로그 확인
```bash
# EC2에서
docker logs -f langchain-backend
docker logs -f langchain-postgres

# 특정 요청 추적
docker logs langchain-backend | grep "request_id=..."
```

### GitHub Actions 로그
- GitHub 저장소 → **Actions** 탭
- 최근 워크플로우 실행 클릭
- 각 step별 로그 확인

### 배포 알림 (선택사항)
```yaml
# .github/workflows/deploy.yml에 추가
- name: Notify Slack
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 🚨 롤백 전략

### **방법 1: Git 롤백**
```bash
# EC2에서
cd /opt/langchain
git log --oneline  # 이전 커밋 확인
git reset --hard <commit-hash>
docker-compose up -d --build
```

### **방법 2: Docker 이미지 태그 사용**
```bash
# 배포 전 이미지 태그 저장
docker tag langchain-backend:latest langchain-backend:backup-$(date +%Y%m%d%H%M%S)

# 롤백 시
docker tag langchain-backend:backup-20250118153000 langchain-backend:latest
docker-compose up -d
```

### **방법 3: 자동 롤백 (GitHub Actions)**
```yaml
- name: Rollback on failure
  if: failure()
  run: |
    ssh -i ~/.ssh/deploy_key $EC2_USER@$EC2_HOST << 'ENDSSH'
      cd ${{ secrets.DEPLOY_PATH }}
      git reset --hard HEAD~1
      docker-compose up -d --build
    ENDSSH
```

---

## 🔐 보안 체크리스트

- [ ] SSH Private Key는 GitHub Secrets에만 저장
- [ ] EC2 보안 그룹: SSH(22)는 본인 IP만, API(8000)는 필요한 IP만
- [ ] `.env` 파일은 `.gitignore`에 추가 (절대 커밋 금지)
- [ ] PostgreSQL 비밀번호는 강력하게 설정
- [ ] HTTPS 사용 (Let's Encrypt + nginx 또는 ALB)
- [ ] 정기적인 보안 패치 (`apt update && apt upgrade`)
- [ ] Docker 이미지 최소화 (불필요한 패키지 제거)

---

## 📈 성능 최적화

### 1. Docker 이미지 최적화
```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements_rag.txt .
RUN pip install --no-cache-dir --user -r requirements_rag.txt

FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
COPY . /app
WORKDIR /app
CMD ["python", "-u", "main.py"]
```

### 2. 모델 캐싱
```yaml
# docker-compose.yml
volumes:
  - model_cache:/root/.cache/huggingface  # 재빌드 시에도 모델 유지
```

### 3. GPU 메모리 최적화
```python
# app/service/chat_service.py
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
)
```

---

## 🧪 배포 테스트

### 로컬에서 테스트
```bash
# Docker Compose로 로컬 환경 실행
docker-compose up --build

# API 테스트
curl http://localhost:8000/docs
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d '{"message":"안녕"}'
```

### Staging 환경 (선택사항)
- `develop` 브랜치 → Staging EC2
- `main` 브랜치 → Production EC2

```yaml
# .github/workflows/deploy-staging.yml
on:
  push:
    branches:
      - develop
env:
  EC2_HOST: ${{ secrets.STAGING_EC2_HOST }}
```

---

## 📚 추가 자료

- [EC2_SETUP.md](./EC2_SETUP.md) - EC2 인스턴스 초기 설정
- [GITHUB_SECRETS_SETUP.md](./GITHUB_SECRETS_SETUP.md) - GitHub Secrets 설정
- [Docker Compose 공식 문서](https://docs.docker.com/compose/)
- [GitHub Actions 공식 문서](https://docs.github.com/en/actions)

---

## 🤝 문의 및 지원

문제 발생 시:
1. GitHub Actions 로그 확인
2. EC2에서 `docker logs -f langchain-backend` 확인
3. Issue 생성 또는 팀 채널에 문의

