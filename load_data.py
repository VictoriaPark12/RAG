"""데이터를 벡터 스토어에 로드하는 스크립트."""

import asyncio
import json
import os
from pathlib import Path

import requests


async def load_movie_reviews():
    """app/data/ 폴더의 JSON 파일들을 읽어서 벡터 스토어에 추가."""

    # 데이터 폴더 경로
    data_dir = Path("app/data")

    if not data_dir.exists():
        print(f"ERROR: 데이터 폴더를 찾을 수 없습니다: {data_dir}")
        return

    # 모든 JSON 파일 찾기
    json_files = list(data_dir.glob("*.json"))
    print(f"총 {len(json_files)}개의 JSON 파일을 찾았습니다.")

    # API 엔드포인트
    api_url = "http://localhost:8000/documents/batch"

    all_documents = []

    # 각 파일 읽기
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 리뷰 데이터 처리
            for review in data:
                # 문서 내용 생성
                content = f"""영화 ID: {review.get('movie_id', 'N/A')}
작성자: {review.get('author', 'N/A')}
평점: {review.get('rating', 'N/A')}/10
날짜: {review.get('date', 'N/A')}

리뷰:
{review.get('review', '')}
"""

                # 메타데이터
                metadata = {
                    "movie_id": review.get("movie_id", ""),
                    "review_id": review.get("review_id", ""),
                    "author": review.get("author", ""),
                    "rating": review.get("rating", ""),
                    "date": review.get("date", ""),
                    "source": str(json_file.name),
                }

                all_documents.append({
                    "content": content,
                    "metadata": metadata
                })

        except Exception as e:
            print(f"ERROR: {json_file} 파일 처리 중 오류: {e}")
            continue

    print(f"\n총 {len(all_documents)}개의 문서를 준비했습니다.")

    if not all_documents:
        print("ERROR: 로드할 문서가 없습니다.")
        return

    # 배치로 나누어 전송 (한 번에 너무 많으면 느릴 수 있음)
    batch_size = 50
    total_batches = (len(all_documents) + batch_size - 1) // batch_size

    print(f"\n{total_batches}개의 배치로 나누어 업로드합니다...")

    for i in range(0, len(all_documents), batch_size):
        batch = all_documents[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        try:
            print(f"배치 {batch_num}/{total_batches} 업로드 중... ({len(batch)}개 문서)")

            response = requests.post(
                api_url,
                json={"documents": batch},
                timeout=300  # 5분 타임아웃
            )

            if response.status_code == 200:
                result = response.json()
                print(f"  [OK] 성공: {result.get('message', 'OK')}")
            else:
                print(f"  [ERROR] 실패: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"  [ERROR] 에러: {e}")
            continue

    print("\n" + "=" * 60)
    print("데이터 로드 완료!")
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("영화 리뷰 데이터를 벡터 스토어에 로드합니다")
    print("=" * 60)
    print("\n[!] 주의: 백엔드 서버가 실행 중이어야 합니다!")
    print("   서버 주소: http://localhost:8000\n")

    # 서버 연결 확인
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("[OK] 서버 연결 확인 완료\n")
        else:
            print("[ERROR] 서버가 정상 응답하지 않습니다.")
            exit(1)
    except Exception as e:
        print(f"[ERROR] 서버에 연결할 수 없습니다: {e}")
        print("\n백엔드 서버를 먼저 실행해주세요:")
        print("  cd app && python main.py")
        exit(1)

    # 데이터 로드 실행
    asyncio.run(load_movie_reviews())

