const FREE_CHAT_STORAGE_KEY = 'janus_free_chats_v1';
const FREE_CHAT_LIMIT = 100;

interface FreeChatState {
  date: string;
  count: number;
}

const todayString = () => new Date().toISOString().split('T')[0];

const normalizeState = (stored: string | null): FreeChatState => {
  const today = todayString();
  if (!stored) {
    return { date: today, count: 0 };
  }

  try {
    const parsed = JSON.parse(stored) as FreeChatState;
    if (!parsed || typeof parsed.date !== 'string' || typeof parsed.count !== 'number') {
      return { date: today, count: 0 };
    }
    if (parsed.date !== today) {
      return { date: today, count: 0 };
    }
    return parsed;
  } catch {
    return { date: today, count: 0 };
  }
};

export function readFreeChatState(): FreeChatState {
  if (typeof window === 'undefined') {
    return { date: todayString(), count: 0 };
  }

  try {
    const stored = window.localStorage.getItem(FREE_CHAT_STORAGE_KEY);
    return normalizeState(stored);
  } catch {
    return { date: todayString(), count: 0 };
  }
}

const persistState = (state: FreeChatState): void => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(FREE_CHAT_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore storage errors.
  }
};

export function setFreeChatCount(count: number): FreeChatState {
  const safeCount = Math.max(0, Math.min(FREE_CHAT_LIMIT, Math.floor(count)));
  const state = { date: todayString(), count: safeCount };
  persistState(state);
  return state;
}

export function incrementFreeChatCount(): FreeChatState {
  const state = readFreeChatState();
  const next = {
    date: state.date,
    count: Math.min(FREE_CHAT_LIMIT, state.count + 1),
  };
  persistState(next);
  return next;
}

export function remainingFreeChats(): number {
  const state = readFreeChatState();
  return Math.max(0, FREE_CHAT_LIMIT - state.count);
}

export function hasFreeChatRemaining(): boolean {
  return remainingFreeChats() > 0;
}

export { FREE_CHAT_LIMIT };
