'use client';

import { useState } from 'react';
import type { ArenaResponse, ArenaWinner } from '@/types/chat';
import { MarkdownContent } from '@/lib/markdown-renderer';

type ArenaComparisonProps = {
  promptId: string;
  responseA: ArenaResponse;
  responseB: ArenaResponse;
  voted?: boolean;
  winner?: ArenaWinner;
  modelA?: string;
  modelB?: string;
  error?: string;
  onVote: (winner: ArenaWinner) => Promise<void>;
};

export function ArenaComparison({
  promptId,
  responseA,
  responseB,
  voted,
  winner,
  modelA,
  modelB,
  error,
  onVote,
}: ArenaComparisonProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [revealed, setRevealed] = useState(false);

  const handleVote = async (selection: ArenaWinner) => {
    if (voted || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onVote(selection);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isLoading = !responseA?.content && !responseB?.content;
  const canVote = Boolean(promptId) && !isLoading;

  return (
    <div className="arena-comparison">
      {error && (
        <div className="arena-error">
          <p>Unable to complete arena action.</p>
          <span>{error}</span>
        </div>
      )}
      <div className="arena-columns">
        <div className="arena-card">
          <div className="arena-card-header">Response A</div>
          {isLoading ? (
            <div className="arena-skeleton" />
          ) : (
            <MarkdownContent content={responseA?.content || ''} />
          )}
        </div>
        <div className="arena-card">
          <div className="arena-card-header">Response B</div>
          {isLoading ? (
            <div className="arena-skeleton" />
          ) : (
            <MarkdownContent content={responseB?.content || ''} />
          )}
        </div>
      </div>

      <div className="arena-actions">
        {!voted ? (
          <>
            <button
              type="button"
              className="arena-vote-button"
              onClick={() => handleVote('A')}
              disabled={isSubmitting || !canVote}
            >
              A is better
            </button>
            <button
              type="button"
              className="arena-vote-button"
              onClick={() => handleVote('B')}
              disabled={isSubmitting || !canVote}
            >
              B is better
            </button>
            <button
              type="button"
              className="arena-vote-button ghost"
              onClick={() => handleVote('tie')}
              disabled={isSubmitting || !canVote}
            >
              Tie
            </button>
            <button
              type="button"
              className="arena-vote-button ghost"
              onClick={() => handleVote('both_bad')}
              disabled={isSubmitting || !canVote}
            >
              Both bad
            </button>
          </>
        ) : (
          <div className="arena-vote-confirmation">
            <span>Vote recorded{winner ? ` (${winner})` : ''}.</span>
            <button
              type="button"
              className="arena-reveal-button"
              onClick={() => setRevealed(true)}
              disabled={!modelA || !modelB}
            >
              Reveal models
            </button>
            {revealed && modelA && modelB && (
              <div className="arena-reveal">
                A: {modelA} · B: {modelB}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
