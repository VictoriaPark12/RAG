# LangChain Hello World with pgvector

이 프로젝트는 LangChain과 pgvector를 연동하는 기본 예제입니다.

## 구성

- **langchain-app**: LangChain 헬로월드 애플리케이션 컨테이너
- **postgres**: pgvector 확장이 포함된 PostgreSQL 컨테이너

## 기술 스택

- **LangChain**: `langchain-postgres` 패키지 사용 (최신 권장 방식)
- **드라이버**: `psycopg` (psycopg3) 사용
- **벡터 스토어**: `PGVector`

## 실행 방법

1. Docker Compose로 컨테이너 실행:
```bash
docker-compose up --build
```

2. 컨테이너 상태 확인:
```bash
docker-compose ps
```

3. 로그 확인:
```bash
docker-compose logs -f langchain-app
```

4. 컨테이너 중지:
```bash
docker-compose down
```

5. 데이터 볼륨까지 삭제하려면:
```bash
docker-compose down -v
```

## 환경 변수

`docker-compose.yml`(또는 `.env`)에서 다음 환경 변수를 설정할 수 있습니다:

- `PGVECTOR_HOST`: PostgreSQL 호스트 (기본값: postgres)
- `PGVECTOR_PORT`: PostgreSQL 포트 (기본값: 5432)
- `PGVECTOR_DATABASE`: 데이터베이스 이름 (기본값: langchain)
- `PGVECTOR_USER`: 데이터베이스 사용자 (기본값: langchain)
- `PGVECTOR_PASSWORD`: 데이터베이스 비밀번호 (기본값: langchain)

## 애플리케이션 동작

1. `PGVector`로 PostgreSQL 연결 및 벡터 스토어 생성
2. pgvector 확장 자동 활성화
3. 샘플 문서를 벡터 스토어에 추가
4. 유사도 검색 수행

## 주요 특징

- **최신 API**: `langchain-postgres`의 `PGVector` 사용
- **자동 확장 활성화**: `init-pgvector.sql`로 pgvector 확장 자동 활성화
- **간단한 사용법**: 최소한의 설정으로 벡터 검색 구현

## 참고사항

- 현재는 `FakeEmbeddings`를 사용하여 API 키 없이 동작합니다
- 프로덕션 환경에서는 실제 임베딩 모델을 사용하세요:
  ```python
  from langchain_openai import OpenAIEmbeddings
  embeddings = OpenAIEmbeddings()  # OPENAI_API_KEY 환경변수 필요
  ```
- PostgreSQL 데이터는 `postgres_data` 볼륨에 영구 저장됩니다
- `psycopg` 드라이버를 사용하므로 연결 문자열은 `postgresql+psycopg://` 형식입니다

