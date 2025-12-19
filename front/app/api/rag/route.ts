import { NextResponse } from "next/server";

export async function POST(req: Request) {
  // RAG는 항상 백엔드로 연결 (벡터 스토어 필요)
  let backendBaseUrl = process.env.BACKEND_BASE_URL ?? "http://localhost:8000";

  // URL 정리: 끝의 슬래시, 점, 기타 문자 제거
  backendBaseUrl = backendBaseUrl.trim().replace(/[\/\.]+$/, "");

  // 디버깅: 환경 변수 확인
  console.log("[RAG] Backend URL:", backendBaseUrl);
  console.log("[RAG] Environment variables:", {
    BACKEND_BASE_URL: process.env.BACKEND_BASE_URL ? "SET" : "NOT SET",
    VERCEL: process.env.VERCEL,
  });

  const body = await req.text();

  try {
    // 타임아웃 설정 (30초)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const upstream = await fetch(`${backendBaseUrl}/rag`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const contentType = upstream.headers.get("content-type") ?? "application/json";
    const text = await upstream.text();

    if (!upstream.ok) {
      console.error(`Backend error: ${upstream.status} - ${text}`);
      return new NextResponse(
        JSON.stringify({ detail: `Backend error: ${upstream.status} - ${text}` }),
        {
          status: upstream.status,
          headers: {
            "content-type": "application/json",
          },
        }
      );
    }

    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "content-type": contentType,
      },
    });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    const isTimeout = errorMessage.includes("aborted") || errorMessage.includes("timeout");
    const isNetworkError = errorMessage.includes("fetch failed") || errorMessage.includes("ECONNREFUSED") || errorMessage.includes("ENOTFOUND");

    console.error("[RAG] Failed to connect to backend:", error);
    console.error("[RAG] Backend URL attempted:", backendBaseUrl);
    console.error("[RAG] Error details:", errorMessage);
    console.error("[RAG] Error type:", {
      isTimeout,
      isNetworkError,
      errorName: error instanceof Error ? error.name : "Unknown",
    });

    let detailMessage = `Failed to connect to backend at ${backendBaseUrl}.`;

    if (isTimeout) {
      detailMessage += " Connection timeout. The backend server may be slow or not responding.";
    } else if (isNetworkError) {
      detailMessage += " Network error. Please check: 1) EC2 security group allows port 8000 from 0.0.0.0/0, 2) Backend service is running on EC2, 3) Backend is bound to 0.0.0.0:8000 (not localhost).";
    } else {
      detailMessage += " Make sure the backend server is running and BACKEND_BASE_URL is set in Vercel environment variables.";
    }

    return new NextResponse(
      JSON.stringify({
        detail: detailMessage,
        backendUrl: backendBaseUrl,
        errorType: isTimeout ? "timeout" : isNetworkError ? "network" : "unknown",
      }),
      {
        status: 503,
        headers: {
          "content-type": "application/json",
        },
      }
    );
  }
}


