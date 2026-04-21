import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.FRIDAY_BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  const body = await req.text();

  const upstream = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body,
    cache: "no-store",
  });

  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text();
    return NextResponse.json(
      { error: "Failed to proxy Friday stream", details: text },
      { status: 502 },
    );
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}

export async function GET() {
  const upstream = await fetch(`${BACKEND_URL}/workspace`, {
    method: "GET",
    cache: "no-store",
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return NextResponse.json(
      { error: "Failed to fetch workspace", details: text },
      { status: 502 },
    );
  }

  const payload = await upstream.json();
  return NextResponse.json(payload);
}
