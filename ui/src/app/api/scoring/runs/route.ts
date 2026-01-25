import { NextRequest, NextResponse } from 'next/server';

const SCORING_SERVICE_URL =
  process.env.SCORING_SERVICE_URL || 'https://janus-scoring-service.onrender.com';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${SCORING_SERVICE_URL}/api/runs${searchParams ? `?${searchParams}` : ''}`;

  const response = await fetch(url, { cache: 'no-store' });
  const data = await response.json();

  return NextResponse.json(data, { status: response.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  const response = await fetch(`${SCORING_SERVICE_URL}/api/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
