import type { NextRequest } from 'next/server';

const RATE_LIMIT = 5;

type IpChatRecord = {
  date: string;
  count: number;
};

type RateLimitStore = Map<string, IpChatRecord>;

declare global {
  // eslint-disable-next-line no-var
  var __janusRateLimitStore: RateLimitStore | undefined;
}

const getStore = (): RateLimitStore => {
  if (!globalThis.__janusRateLimitStore) {
    globalThis.__janusRateLimitStore = new Map();
  }
  return globalThis.__janusRateLimitStore;
};

const todayString = () => new Date().toISOString().split('T')[0];

const buildKey = (ipAddress: string, date: string) => `${ipAddress}:${date}`;

export const checkIpRateLimit = async (
  ipAddress: string,
  limit: number = RATE_LIMIT
): Promise<{ allowed: boolean; remaining: number; used: number }> => {
  const today = todayString();
  const store = getStore();
  const record = store.get(buildKey(ipAddress, today));
  const used = record?.count ?? 0;
  const remaining = Math.max(0, limit - used);
  const allowed = used < limit;
  return { allowed, remaining, used };
};

export const incrementIpChatCount = async (ipAddress: string): Promise<void> => {
  const today = todayString();
  const store = getStore();
  const key = buildKey(ipAddress, today);
  const existing = store.get(key);
  store.set(key, { date: today, count: (existing?.count ?? 0) + 1 });
};

export const getClientIp = (request: NextRequest): string => {
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    return forwarded.split(',')[0]?.trim() || 'unknown';
  }
  const requestIp = (request as { ip?: string }).ip;
  return (
    request.headers.get('x-real-ip') ||
    request.headers.get('cf-connecting-ip') ||
    requestIp ||
    'unknown'
  );
};
