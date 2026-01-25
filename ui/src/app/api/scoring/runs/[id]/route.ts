import { NextRequest, NextResponse } from 'next/server';

const SCORING_SERVICE_URL =
  process.env.SCORING_SERVICE_URL || 'https://janus-scoring-service.onrender.com';

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  const response = await fetch(`${SCORING_SERVICE_URL}/api/runs/${id}`, { cache: 'no-store' });
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}

export async function DELETE(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  const response = await fetch(`${SCORING_SERVICE_URL}/api/runs/${id}`, {
    method: 'DELETE',
  });
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
