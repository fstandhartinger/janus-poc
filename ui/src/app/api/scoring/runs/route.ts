import { NextRequest } from 'next/server';
import { SCORING_SERVICE_URL, proxyScoringJson } from '@/lib/scoringProxy';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${SCORING_SERVICE_URL}/api/runs${searchParams ? `?${searchParams}` : ''}`;
  return proxyScoringJson(url);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  return proxyScoringJson(`${SCORING_SERVICE_URL}/api/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}
