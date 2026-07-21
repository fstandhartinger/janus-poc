import { SCORING_SERVICE_URL, proxyScoringJson } from '@/lib/scoringProxy';

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> }
) {
  const { id } = await context.params;
  return proxyScoringJson(`${SCORING_SERVICE_URL}/api/runs/${id}/summary`);
}
