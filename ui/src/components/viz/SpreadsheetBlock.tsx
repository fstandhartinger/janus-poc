'use client';

import { useMemo, useState } from 'react';

type CellValue = string | number | boolean | null;

type Row = CellValue[];
type SpreadsheetData = Row[];

interface SpreadsheetBlockProps {
  data: SpreadsheetData;
  hasHeader?: boolean;
}

export function SpreadsheetBlock({ data, hasHeader = true }: SpreadsheetBlockProps) {
  const [sortColumn, setSortColumn] = useState<number | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');
  const [filter, setFilter] = useState('');

  const headers = hasHeader && data.length > 0 ? data[0] : null;
  const rows = hasHeader && data.length > 0 ? data.slice(1) : data;

  const filteredRows = useMemo(() => {
    if (!filter.trim()) return rows;

    const query = filter.toLowerCase();
    return rows.filter((row) =>
      row.some((cell) => String(cell).toLowerCase().includes(query))
    );
  }, [rows, filter]);

  const sortedRows = useMemo(() => {
    if (sortColumn === null) return filteredRows;

    return [...filteredRows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal ?? '');
      const bStr = String(bVal ?? '');
      const cmp = aStr.localeCompare(bStr);
      return sortDirection === 'asc' ? cmp : -cmp;
    });
  }, [filteredRows, sortColumn, sortDirection]);

  const handleSort = (colIndex: number) => {
    if (sortColumn === colIndex) {
      setSortDirection((direction) => (direction === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(colIndex);
      setSortDirection('asc');
    }
  };

  const copyToClipboard = async () => {
    const tsv = data.map((row) => row.join('\t')).join('\n');
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(tsv);
        return;
      } catch {
        // Fall through to legacy method.
      }
    }

    const textarea = document.createElement('textarea');
    textarea.value = tsv;
    textarea.setAttribute('readonly', 'true');
    textarea.style.position = 'absolute';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    document.body.removeChild(textarea);
  };

  const downloadCSV = () => {
    const csv = data
      .map((row) =>
        row
          .map((cell) => {
            const str = String(cell ?? '');
            if (str.includes(',') || str.includes('"') || str.includes('\n')) {
              return `"${str.replace(/"/g, '""')}"`;
            }
            return str;
          })
          .join(',')
      )
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'data.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="spreadsheet-block">
      <div className="spreadsheet-toolbar">
        <input
          type="text"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Filter..."
          className="spreadsheet-filter"
          aria-label="Filter spreadsheet"
        />
        <div className="spreadsheet-actions">
          <button type="button" onClick={copyToClipboard} title="Copy to clipboard" aria-label="Copy to clipboard">
            <CopyIcon />
          </button>
          <button type="button" onClick={downloadCSV} title="Download CSV" aria-label="Download CSV">
            <DownloadIcon />
          </button>
        </div>
      </div>

      <div className="spreadsheet-scroll">
        <table className="spreadsheet-table" aria-label="Spreadsheet data" tabIndex={0}>
          {headers && (
            <thead>
              <tr>
                {headers.map((header, index) => (
                  <th
                    key={index}
                    onClick={() => handleSort(index)}
                    className="spreadsheet-header"
                    scope="col"
                  >
                    <span>{String(header)}</span>
                    {sortColumn === index && (
                      <span className="sort-indicator">
                        {sortDirection === 'asc' ? '^' : 'v'}
                      </span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
          )}
          <tbody>
            {sortedRows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="spreadsheet-cell">
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="spreadsheet-footer">
        {sortedRows.length} rows
        {filter && ` (filtered from ${rows.length})`}
      </div>
    </div>
  );
}

function formatCell(value: CellValue): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') {
    return value.toLocaleString();
  }
  return String(value);
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}
