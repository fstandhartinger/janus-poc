'use client';

import { useCallback } from 'react';
import { useSettingsStore } from '@/store/settings';
import { createArenaCompletion, submitArenaVote } from '@/lib/api';
import type { ArenaCompletionResponse, ArenaVoteResponse, ArenaWinner, ChatCompletionRequest } from '@/types/chat';

export const useArena = () => {
  const arenaMode = useSettingsStore((state) => state.arenaMode);
  const setArenaMode = useSettingsStore((state) => state.setArenaMode);

  const requestArenaCompletion = useCallback(
    async (
      request: ChatCompletionRequest,
      signal?: AbortSignal
    ): Promise<ArenaCompletionResponse> => {
      return createArenaCompletion(request, signal);
    },
    []
  );

  const submitVote = useCallback(
    async (promptId: string, winner: ArenaWinner): Promise<ArenaVoteResponse> => {
      return submitArenaVote({ prompt_id: promptId, winner });
    },
    []
  );

  return {
    arenaMode,
    setArenaMode,
    requestArenaCompletion,
    submitVote,
  };
};
