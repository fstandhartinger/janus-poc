'use client';

import { useState } from 'react';

type SessionSaveDialogProps = {
  defaultName: string;
  defaultDescription: string;
  detectedDomains: string[];
  existingDomains?: string[];
  onSave: (name: string, description: string, domains: string[]) => void;
  onCancel: () => void;
};

export function SessionSaveDialog({
  defaultName,
  defaultDescription,
  detectedDomains,
  existingDomains,
  onSave,
  onCancel,
}: SessionSaveDialogProps) {
  const [name, setName] = useState(defaultName);
  const [description, setDescription] = useState(defaultDescription);
  const [selectedDomains, setSelectedDomains] = useState<string[]>(
    existingDomains || detectedDomains
  );
  const [customDomain, setCustomDomain] = useState('');
  const [nameError, setNameError] = useState<string | null>(null);
  const [domainError, setDomainError] = useState<string | null>(null);

  const handleNameChange = (value: string) => {
    setName(value);
    setNameError(null);
  };

  const handleToggleDomain = (domain: string) => {
    setSelectedDomains((prev) =>
      prev.includes(domain)
        ? prev.filter((d) => d !== domain)
        : [...prev, domain]
    );
    setDomainError(null);
  };

  const handleAddCustomDomain = () => {
    const trimmed = customDomain.trim().toLowerCase();
    if (!trimmed) return;

    // Basic domain validation
    const domainPattern = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/;
    if (!domainPattern.test(trimmed)) {
      setDomainError('Invalid domain format');
      return;
    }

    if (!selectedDomains.includes(trimmed)) {
      setSelectedDomains((prev) => [...prev, trimmed]);
    }
    setCustomDomain('');
    setDomainError(null);
  };

  const handleRemoveDomain = (domain: string) => {
    setSelectedDomains((prev) => prev.filter((d) => d !== domain));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate name
    const trimmedName = name.trim();
    if (!trimmedName) {
      setNameError('Session name is required');
      return;
    }
    const namePattern = /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/;
    if (!namePattern.test(trimmedName)) {
      setNameError('Name must start with a letter or number and contain only letters, numbers, dashes, and underscores');
      return;
    }

    // Validate domains
    if (selectedDomains.length === 0) {
      setDomainError('At least one domain is required');
      return;
    }

    onSave(trimmedName, description.trim(), selectedDomains);
  };

  // Combine detected domains with any existing domains that aren't in detected
  const allAvailableDomains = [
    ...detectedDomains,
    ...(existingDomains || []).filter((d) => !detectedDomains.includes(d)),
  ];

  return (
    <div className="session-save-overlay">
      <form className="session-save-dialog" onSubmit={handleSubmit}>
        <h3>Save Session</h3>

        <div className="session-save-field">
          <label htmlFor="session-name">Session Name</label>
          <input
            id="session-name"
            type="text"
            value={name}
            onChange={(e) => handleNameChange(e.target.value)}
            placeholder="e.g., MyTwitter"
            maxLength={50}
            autoFocus
          />
          {nameError && <p className="session-save-error">{nameError}</p>}
        </div>

        <div className="session-save-field">
          <label htmlFor="session-description">Description (optional)</label>
          <input
            id="session-description"
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description"
            maxLength={500}
          />
        </div>

        <div className="session-save-field">
          <label>Domains</label>
          <p className="session-save-hint">
            Select which domains this session applies to:
          </p>

          {allAvailableDomains.length > 0 && (
            <div className="session-domain-checkboxes">
              {allAvailableDomains.map((domain) => (
                <label key={domain} className="session-domain-checkbox">
                  <input
                    type="checkbox"
                    checked={selectedDomains.includes(domain)}
                    onChange={() => handleToggleDomain(domain)}
                  />
                  <span>{domain}</span>
                </label>
              ))}
            </div>
          )}

          <div className="session-selected-domains">
            {selectedDomains
              .filter((d) => !allAvailableDomains.includes(d))
              .map((domain) => (
                <span key={domain} className="session-domain-tag">
                  {domain}
                  <button
                    type="button"
                    onClick={() => handleRemoveDomain(domain)}
                    aria-label={`Remove ${domain}`}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6l-12 12" />
                    </svg>
                  </button>
                </span>
              ))}
          </div>

          <div className="session-add-domain">
            <input
              type="text"
              value={customDomain}
              onChange={(e) => {
                setCustomDomain(e.target.value);
                setDomainError(null);
              }}
              placeholder="Add custom domain..."
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddCustomDomain();
                }
              }}
            />
            <button type="button" onClick={handleAddCustomDomain}>
              Add
            </button>
          </div>

          {domainError && <p className="session-save-error">{domainError}</p>}
        </div>

        <div className="session-save-actions">
          <button type="button" className="session-save-cancel" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="session-save-submit">
            Save Session
          </button>
        </div>
      </form>
    </div>
  );
}
