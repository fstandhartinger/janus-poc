import { NextRequest, NextResponse } from 'next/server';

const SCORING_SERVICE_URL =
  process.env.SCORING_SERVICE_URL || 'https://janus-scoring-service.onrender.com';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${SCORING_SERVICE_URL}/api/runs/${id}/results${
    searchParams ? `?${searchParams}` : ''
  }`;

  const response = await fetch(url, { cache: 'no-store' });
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
