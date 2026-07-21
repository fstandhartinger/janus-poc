import { NextRequest } from 'next/server';
import { SCORING_SERVICE_URL, proxyScoringJson } from '@/lib/scoringProxy';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${SCORING_SERVICE_URL}/api/runs/${id}/results${
    searchParams ? `?${searchParams}` : ''
  }`;
  return proxyScoringJson(url);
}
