import { NextResponse } from "next/server";

const BACKEND_URL = process.env.FRIDAY_BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  const upstream = await fetch(`${BACKEND_URL}/agents`, {
    method: "GET",
    cache: "no-store",
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return NextResponse.json(
      { error: "Failed to fetch agents", details: text },
      { status: 502 },
    );
  }

  const payload = await upstream.json();
  return NextResponse.json(payload);
}
