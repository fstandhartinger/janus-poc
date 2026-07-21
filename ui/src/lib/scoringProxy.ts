import { NextResponse } from 'next/server';

export const SCORING_SERVICE_URL =
  process.env.SCORING_SERVICE_URL || 'https://janus-scoring-service.onrender.com';

export const SCORING_UNAVAILABLE_BODY = {
  error: 'scoring_service_unavailable',
  message:
    'The scoring service is temporarily offline. Runs, results and the scoring leaderboard are unavailable right now.',
};

/**
 * Proxy a JSON request to the scoring service without ever throwing.
 *
 * The scoring service runs on Render and can be suspended (no free tier for
 * team workspaces) — in that state Render answers with an HTML 503 page, so a
 * naive `response.json()` explodes and the Next route 500s. Instead we map
 * every non-JSON / network failure to a clean 503 JSON payload the UI can
 * detect and message.
 */
export async function proxyScoringJson(
  url: string,
  init?: RequestInit,
  extraHeaders?: Record<string, string>
): Promise<NextResponse> {
  try {
    const response = await fetch(url, { cache: 'no-store', ...init });
    const data = await response.json();
    return NextResponse.json(data, {
      status: response.status,
      headers: extraHeaders,
    });
  } catch {
    return NextResponse.json(SCORING_UNAVAILABLE_BODY, { status: 503 });
  }
}
