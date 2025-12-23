// @ts-ignore - Next.js 타입 정의
import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // 백엔드 URL 설정 (환경 변수만 사용)
    // @ts-ignore - Next.js 서버 사이드에서 process.env는 사용 가능하지만 타입 정의가 불완전함
    let backendBaseUrl = process.env.BACKEND_BASE_URL;
    
    // 디버깅: 환경 변수 값 로그 (포트 확인용)
    console.log(`[API Route] BACKEND_BASE_URL from env: ${backendBaseUrl || "NOT SET"}`);
    
    if (!backendBaseUrl) {
      console.error("[API Route] BACKEND_BASE_URL environment variable is not set");
      return NextResponse.json(
        { detail: "Backend URL is not configured. Please set BACKEND_BASE_URL environment variable." },
        { status: 500 }
      );
    }

    // URL 정규화: 포트가 없으면 8000 추가, trailing slash 제거
    backendBaseUrl = backendBaseUrl.trim().replace(/\/$/, ""); // trailing slash 제거
    
    // URL 파싱 및 포트 확인
    try {
      const urlObj = new URL(backendBaseUrl);
      // 포트가 명시되지 않았거나 포트 80인 경우 포트 8000으로 변경
      if (!urlObj.port || urlObj.port === "80") {
        urlObj.port = "8000";
        backendBaseUrl = urlObj.toString().replace(/\/$/, "");
        console.log(`[API Route] Port not specified or port 80 detected, using port 8000: ${backendBaseUrl}`);
      }
    } catch (urlError) {
      console.error(`[API Route] Invalid BACKEND_BASE_URL format: ${backendBaseUrl}`, urlError);
      return NextResponse.json(
        { detail: `Invalid BACKEND_BASE_URL format: ${backendBaseUrl}. Expected format: http://host:port` },
        { status: 500 }
      );
    }
    
    console.log(`[API Route] Using backend URL: ${backendBaseUrl}`);

    const backendUrl = `${backendBaseUrl}/rag`;

    console.log(`[API Route] Proxying to backend: ${backendUrl}`);

    // EC2 백엔드로 프록시 요청
    // Vercel 서버리스 함수 타임아웃: 기본 10초, 최대 60초 (Pro 플랜)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 50000); // 50초 타임아웃
    
    let response: Response;
    try {
      response = await fetch(backendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } catch (fetchError) {
      clearTimeout(timeoutId);
      
      // 상세한 에러 로깅
      console.error(`[API Route] ========== FETCH ERROR ==========`);
      console.error(`[API Route] Backend URL: ${backendUrl}`);
      console.error(`[API Route] Error name: ${fetchError instanceof Error ? fetchError.name : "Unknown"}`);
      console.error(`[API Route] Error message: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`);
      
      // cause 체인 확인 (Node.js fetch의 경우)
      const cause = (fetchError as any)?.cause;
      if (cause) {
        console.error(`[API Route] Error cause:`, JSON.stringify(cause, null, 2));
        console.error(`[API Route] Cause code: ${cause.code || "N/A"}`);
        console.error(`[API Route] Cause syscall: ${cause.syscall || "N/A"}`);
        console.error(`[API Route] Cause address: ${cause.address || "N/A"}`);
        console.error(`[API Route] Cause port: ${cause.port || "N/A"}`);
      }
      console.error(`[API Route] ==================================`);
      
      // 더 자세한 에러 메시지
      let errorMessage = "Unknown fetch error";
      if (fetchError instanceof Error) {
        const errorDetails = cause ? ` (${cause.code || cause.message || JSON.stringify(cause)})` : "";
        
        if (fetchError.name === "AbortError") {
          errorMessage = "Backend request timeout. The server may be taking too long to respond.";
        } else if (fetchError.message.includes("ECONNREFUSED") || (cause && cause.code === "ECONNREFUSED")) {
          errorMessage = `Cannot connect to backend server at ${backendUrl}. The server may not be running or the port is incorrect.${errorDetails}`;
        } else if (fetchError.message.includes("ENOTFOUND") || (cause && cause.code === "ENOTFOUND")) {
          errorMessage = `DNS lookup failed for ${backendUrl}. Check if the hostname is correct.${errorDetails}`;
        } else if (fetchError.message.includes("fetch failed")) {
          errorMessage = `Network error: Unable to reach backend server at ${backendUrl}.${errorDetails} Check network connectivity, backend status, and EC2 security group settings.`;
        } else {
          errorMessage = `${fetchError.message}${errorDetails}`;
        }
      }
      
      return NextResponse.json(
        { detail: errorMessage },
        { status: 500 }
      );
    }
    
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[API Route] Backend error: ${response.status}`, errorText);
      return NextResponse.json(
        { detail: errorText || `Backend error: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("[API Route] Error:", error);
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}

