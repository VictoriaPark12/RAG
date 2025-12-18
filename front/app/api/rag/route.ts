import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const backendBaseUrl = process.env.BACKEND_BASE_URL ?? "http://localhost:8000";

  const body = await req.text();

  const upstream = await fetch(`${backendBaseUrl}/rag`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body,
  });

  const contentType = upstream.headers.get("content-type") ?? "application/json";
  const text = await upstream.text();

  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      "content-type": contentType,
    },
  });
}


