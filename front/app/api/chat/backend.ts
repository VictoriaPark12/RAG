// Chat 백엔드 호출 유틸리티 함수
export async function callChatBackend(body: {
  message: string;
  conversation_history?: Array<{ role: string; content: string }>;
}) {
  try {
    // 백엔드 URL 설정 (환경 변수 또는 fallback)
    // NEXT_PUBLIC_ 접두사가 있어야 클라이언트에서 접근 가능
    // Next.js는 빌드 타임에 NEXT_PUBLIC_* 환경 변수를 클라이언트 번들에 포함시킴
    const backendBaseUrl =
      // @ts-ignore - Next.js가 빌드 타임에 주입하는 환경 변수
      (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_BACKEND_BASE_URL) ||
      "http://ec2-13-124-217-222.ap-northeast-2.compute.amazonaws.com:8000";

    const backendUrl = `${backendBaseUrl}/chat`;

    console.log(`[Chat] Calling backend: ${backendUrl}`);

    // EC2 백엔드로 직접 요청
    const response = await fetch(backendUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[Chat] Backend error: ${response.status}`, errorText);
      throw new Error(errorText || `Backend error: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("[Chat] Error:", error);
    throw error instanceof Error ? error : new Error("Unknown error");
  }
}

