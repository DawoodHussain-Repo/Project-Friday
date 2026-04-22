const FALLBACK_BACKEND_URL = "http://localhost:8000";

function resolveBackendUrl(): string {
  const raw = process.env.FRIDAY_BACKEND_URL ?? FALLBACK_BACKEND_URL;

  let parsed: URL;
  try {
    parsed = new URL(raw);
  } catch {
    throw new Error(
      `Invalid FRIDAY_BACKEND_URL: '${raw}'. Expected an absolute URL like http://localhost:8000`,
    );
  }

  return parsed.toString().replace(/\/$/, "");
}

export const FRIDAY_BACKEND_URL = resolveBackendUrl();
