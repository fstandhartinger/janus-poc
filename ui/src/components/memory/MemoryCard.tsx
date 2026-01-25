'use client';

import { useEffect, useState } from 'react';
import type { MemoryRecord } from '@/hooks/useMemories';

type MemoryCardProps = {
  memory: MemoryRecord;
  onEdit: (id: string, updates: Partial<MemoryRecord>) => Promise<void> | void;
  onDelete: (id: string) => Promise<void> | void;
};

function formatRelativeTime(isoDate: string) {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return 'Unknown';
  if (typeof Intl === 'undefined' || !Intl.RelativeTimeFormat) {
    return date.toLocaleDateString();
  }

  const diffSeconds = Math.round((date.getTime() - Date.now()) / 1000);
  const absSeconds = Math.abs(diffSeconds);
  const ranges: Array<[Intl.RelativeTimeFormatUnit, number]> = [
    ['year', 60 * 60 * 24 * 365],
    ['month', 60 * 60 * 24 * 30],
    ['week', 60 * 60 * 24 * 7],
    ['day', 60 * 60 * 24],
    ['hour', 60 * 60],
    ['minute', 60],
    ['second', 1],
  ];

  for (const [unit, secondsInUnit] of ranges) {
    if (absSeconds >= secondsInUnit || unit === 'second') {
      const value = Math.round(diffSeconds / secondsInUnit);
      return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(value, unit);
    }
  }

  return 'Just now';
}

export function MemoryCard({ memory, onEdit, onDelete }: MemoryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedCaption, setEditedCaption] = useState(memory.caption);
  const [editedText, setEditedText] = useState(memory.full_text);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEditedCaption(memory.caption);
    setEditedText(memory.full_text);
  }, [memory.caption, memory.full_text]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await Promise.resolve(
        onEdit(memory.id, {
          caption: editedCaption,
          full_text: editedText,
        })
      );
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to update memory:', err);
      setError('Unable to save updates.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditedCaption(memory.caption);
    setEditedText(memory.full_text);
    setIsEditing(false);
    setError(null);
  };

  const handleDelete = async () => {
    setError(null);
    try {
      await Promise.resolve(onDelete(memory.id));
    } catch (err) {
      console.error('Failed to delete memory:', err);
      setError('Unable to delete this memory.');
    }
  };

  return (
    <div className="glass-card memory-card">
      {isEditing ? (
        <div className="memory-card-edit">
          <label className="memory-field">
            <span className="memory-field-label">Caption</span>
            <input
              value={editedCaption}
              onChange={(event) => setEditedCaption(event.target.value)}
              className="memory-input"
              placeholder="Caption"
            />
          </label>
          <label className="memory-field">
            <span className="memory-field-label">Details</span>
            <textarea
              value={editedText}
              onChange={(event) => setEditedText(event.target.value)}
              className="memory-textarea"
              placeholder="Full content"
            />
          </label>
          {error && <p className="memory-error">{error}</p>}
          <div className="memory-edit-actions">
            <button
              type="button"
              onClick={handleSave}
              className="memory-button primary"
              disabled={saving}
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
            <button type="button" onClick={handleCancel} className="memory-button ghost">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="memory-card-header">
            <button
              type="button"
              className="memory-card-summary"
              onClick={() => setIsExpanded((prev) => !prev)}
              aria-expanded={isExpanded}
            >
              <p className="memory-card-caption">{memory.caption}</p>
              <p className="memory-card-time">{formatRelativeTime(memory.created_at)}</p>
            </button>
            <div className="memory-card-actions">
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="memory-icon-button"
                title="Edit"
                aria-label="Edit memory"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M16.5 3.75l3.75 3.75-10.5 10.5-4.5 1.125 1.125-4.5 10.125-10.875z"
                  />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6.75l3.75 3.75" />
                </svg>
              </button>
              <button
                type="button"
                onClick={handleDelete}
                className="memory-icon-button danger"
                title="Delete"
                aria-label="Delete memory"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 7.5h15" />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9.75 7.5v9.75m4.5-9.75v9.75"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6.75 7.5l1.125 11.25a1.5 1.5 0 0 0 1.5 1.25h5.25a1.5 1.5 0 0 0 1.5-1.25L17.25 7.5M9 4.5h6"
                  />
                </svg>
              </button>
            </div>
          </div>
          {isExpanded && (
            <div className="memory-card-expanded">
              <p>{memory.full_text}</p>
            </div>
          )}
          {error && <p className="memory-error">{error}</p>}
        </>
      )}
    </div>
  );
}
