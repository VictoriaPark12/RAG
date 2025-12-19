import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const backendBaseUrl = process.env.BACKEND_BASE_URL ?? "http://localhost:8000";

  const body = await req.text();

  try {
    const upstream = await fetch(`${backendBaseUrl}/rag`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body,
    });

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
    console.error("Failed to connect to backend:", error);
    return new NextResponse(
      JSON.stringify({
        detail: `Failed to connect to backend at ${backendBaseUrl}. Make sure the backend server is running.`,
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


