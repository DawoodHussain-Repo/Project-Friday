import { NextResponse } from "next/server";

import { FRIDAY_BACKEND_URL } from "../../../../lib/config";

export async function GET() {
  const upstream = await fetch(`${FRIDAY_BACKEND_URL}/skills`, {
    method: "GET",
    cache: "no-store",
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return NextResponse.json(
      { error: "Failed to fetch skills", details: text },
      { status: 502 },
    );
  }

  const payload = await upstream.json();
  return NextResponse.json(payload);
}
