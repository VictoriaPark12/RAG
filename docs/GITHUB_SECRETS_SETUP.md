# GitHub Secrets 설정 가이드

GitHub Actions에서 EC2 배포를 위해 필요한 Secrets를 설정하는 방법입니다.

## 📌 필수 Secrets

GitHub 저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### 1. `EC2_SSH_PRIVATE_KEY`
- **설명**: EC2 인스턴스에 SSH 접속하기 위한 Private Key
- **값 생성 방법**:
  ```bash
  # 로컬에서 새 SSH 키 생성
  ssh-keygen -t ed25519 -C "github-actions@langchain-deploy" -f ~/.ssh/langchain_deploy

  # Private Key 내용 복사 (GitHub Secret에 등록)
  cat ~/.ssh/langchain_deploy

  # Public Key 내용 복사 (EC2 인스턴스에 등록)
  cat ~/.ssh/langchain_deploy.pub
  ```

- **EC2에 Public Key 등록**:
  ```bash
  # EC2 인스턴스에 SSH 접속 후
  echo "ssh-ed25519 AAAAC3Nza... github-actions@langchain-deploy" >> ~/.ssh/authorized_keys
  chmod 600 ~/.ssh/authorized_keys
  ```

- **GitHub Secret에 등록할 값**:
  ```
  -----BEGIN OPENSSH PRIVATE KEY-----
  b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
  ... (전체 내용)
  -----END OPENSSH PRIVATE KEY-----
  ```

### 2. `EC2_HOST`
- **설명**: EC2 인스턴스의 Public IP 또는 도메인
- **값 예시**:
  ```
  54.123.45.67
  ```
  또는
  ```
  api.yourdomain.com
  ```

### 3. `EC2_USER`
- **설명**: EC2 SSH 접속 유저명
- **값 예시**:
  ```
  ubuntu
  ```
  (Amazon Linux의 경우 `ec2-user`)

### 4. `DEPLOY_PATH`
- **설명**: EC2 인스턴스 내 애플리케이션 배포 디렉토리 경로
- **값 예시**:
  ```
  /opt/langchain
  ```

---

## 🔐 선택적 Secrets (환경 변수)

배포 시 `.env` 파일을 EC2에 미리 설정해두는 대신, GitHub Secrets로 관리할 수도 있습니다.

### 5. `ENV_FILE` (선택사항)
- **설명**: `.env` 파일 전체 내용
- **값 예시**:
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

- **GitHub Actions에서 사용 방법**:
  ```yaml
  - name: Create .env file
    run: |
      ssh -i ~/.ssh/deploy_key $EC2_USER@$EC2_HOST << 'ENDSSH'
        cd ${{ secrets.DEPLOY_PATH }}
        echo "${{ secrets.ENV_FILE }}" > .env
      ENDSSH
  ```

---

## 📋 설정 확인 체크리스트

- [ ] `EC2_SSH_PRIVATE_KEY`: Private Key 전체 내용 (BEGIN/END 포함)
- [ ] `EC2_HOST`: EC2 Public IP 또는 도메인
- [ ] `EC2_USER`: SSH 유저명 (ubuntu 또는 ec2-user)
- [ ] `DEPLOY_PATH`: 배포 디렉토리 절대 경로
- [ ] EC2에 Public Key 등록 완료
- [ ] EC2에 `/opt/langchain/.env` 파일 존재 (또는 `ENV_FILE` Secret 사용)
- [ ] EC2에 Git 저장소 clone 완료 (`cd /opt/langchain && git clone ...`)

---

## 🧪 테스트 방법

### 로컬에서 SSH 접속 테스트
```bash
ssh -i ~/.ssh/langchain_deploy ubuntu@54.123.45.67
```

### GitHub Actions에서 수동 배포 트리거
1. GitHub 저장소 → **Actions** 탭
2. **Deploy to EC2** 워크플로우 선택
3. **Run workflow** → **Run workflow** 버튼 클릭

### 배포 로그 확인
```bash
# EC2에서 Docker 로그 확인
docker logs -f langchain-backend

# GitHub Actions 로그 확인
# GitHub 저장소 → Actions 탭 → 최근 워크플로우 실행 클릭
```

---

## 🚨 보안 주의사항

1. **Private Key는 절대 Git에 커밋하지 말 것**
2. **EC2 보안 그룹에서 SSH(22) 포트는 본인 IP만 허용**
3. **`.env` 파일도 절대 Git에 커밋하지 말 것** (`.gitignore`에 추가됨)
4. **정기적으로 SSH 키 로테이션** (3-6개월마다)
5. **Secrets 값 변경 시 EC2 설정도 함께 업데이트**

---

## 🔧 트러블슈팅

### "Permission denied (publickey)" 에러
```bash
# EC2에서 권한 확인
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys

# Public Key가 제대로 등록되었는지 확인
cat ~/.ssh/authorized_keys
```

### "Host key verification failed" 에러
- GitHub Actions 워크플로우에 `ssh-keyscan` 단계가 있는지 확인
- 또는 EC2 인스턴스 재생성 후 `known_hosts` 파일 업데이트 필요

### 배포 후 API가 응답하지 않음
```bash
# EC2에서 확인
docker ps  # 컨테이너 실행 상태
docker logs langchain-backend  # 에러 로그
curl http://localhost:8000/docs  # API 응답 확인
```

