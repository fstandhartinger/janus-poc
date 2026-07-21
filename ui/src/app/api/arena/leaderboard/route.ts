import { NextRequest } from 'next/server';
import { SCORING_SERVICE_URL, proxyScoringJson } from '@/lib/scoringProxy';

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${SCORING_SERVICE_URL}/api/arena/leaderboard${
    searchParams ? `?${searchParams}` : ''
  }`;
  return proxyScoringJson(url, undefined, {
    'Cache-Control': 'public, max-age=60, stale-while-revalidate=300',
  });
}
