# Ollama 로컬 설치 및 RAG 실행 가이드

## 1. Ollama 로컬 설치

### Windows
1. https://ollama.com/download 에서 Windows 버전 다운로드
2. 설치 파일 실행
3. 설치 완료 후 자동으로 Ollama 서비스 시작됨

### macOS
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## 2. Ollama 모델 다운로드

터미널/PowerShell에서:

```bash
# 가벼운 모델 (1.3GB) - 추천
ollama pull llama3.2:1b

# 또는 더 강력한 모델 (2GB)
ollama pull llama3.2:3b
```

## 3. Ollama 서버 확인

```bash
# Ollama가 실행 중인지 확인
ollama list
```

출력 예시:
```
NAME              ID              SIZE      MODIFIED
llama3.2:1b       abc123...       1.3 GB    2 hours ago
```

## 4. Python 환경 설정

### 가상환경 생성 및 활성화
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### RAG용 패키지 설치
```bash
pip install -r requirements_rag.txt
```

## 5. PostgreSQL + pgvector 실행 (Docker)

```bash
# pgvector만 Docker로 실행
docker-compose up -d postgres
```

## 6. RAG 애플리케이션 실행

```bash
python app_rag.py
```

## 실행 흐름

```
1. PostgreSQL (Docker) → pgvector
2. Ollama (로컬) → LLM
3. app_rag.py → RAG 체인 실행
   ↓
   질문 → 검색 → LLM 답변 생성
```

## 트러블슈팅

### Ollama 연결 오류
```bash
# Ollama 서비스 재시작 (Windows)
# 작업 관리자에서 Ollama 종료 후 다시 시작

# macOS/Linux
pkill ollama
ollama serve
```

### 포트 충돌
```bash
# Ollama 포트 확인 (기본: 11434)
netstat -ano | findstr :11434
```

### 모델 다운로드 느림
- 모델 크기가 1-2GB이므로 시간이 걸릴 수 있습니다
- 다운로드는 한 번만 하면 됩니다

## 환경 변수 (선택사항)

`.env` 파일 생성:
```env
PGVECTOR_HOST=localhost
PGVECTOR_PORT=5432
PGVECTOR_DATABASE=langchain
PGVECTOR_USER=langchain
PGVECTOR_PASSWORD=langchain

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b
```

## 다른 Ollama 모델 사용

```bash
# 사용 가능한 모델 확인
ollama list

# 다른 모델 다운로드
ollama pull mistral
ollama pull llama3.2:3b
```

`.env` 파일에서 `OLLAMA_MODEL` 변경

## 리소스 사용량

- **llama3.2:1b**: RAM 약 2GB, 빠른 응답
- **llama3.2:3b**: RAM 약 4GB, 더 나은 품질
- **mistral**: RAM 약 8GB, 가장 강력

## 참고 링크

- Ollama 공식 사이트: https://ollama.com
- 모델 라이브러리: https://ollama.com/library
- LangChain Ollama: https://python.langchain.com/docs/integrations/llms/ollama

