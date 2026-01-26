interface ParameterEntry {
  name: string;
  type: string;
  required?: boolean;
  defaultValue?: string;
  description: string;
  children?: ParameterEntry[];
}

interface ParameterTableProps {
  title: string;
  description?: string;
  entries: ParameterEntry[];
  className?: string;
}

interface FlattenedEntry extends ParameterEntry {
  path: string;
  depth: number;
}

function flattenEntries(entries: ParameterEntry[], parentPath = '', depth = 0): FlattenedEntry[] {
  const rows: FlattenedEntry[] = [];

  entries.forEach((entry) => {
    const path = parentPath ? `${parentPath}.${entry.name}` : entry.name;
    rows.push({ ...entry, path, depth });

    if (entry.children && entry.children.length > 0) {
      const childParent = entry.type === 'array' ? `${path}[]` : path;
      rows.push(...flattenEntries(entry.children, childParent, depth + 1));
    }
  });

  return rows;
}

export function ParameterTable({ title, description, entries, className }: ParameterTableProps) {
  const rows = flattenEntries(entries);

  return (
    <div className={`glass-card p-6 space-y-4 ${className ?? ''}`.trim()}>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold text-[#F3F4F6]">{title}</h3>
        {description && <p className="text-sm text-[#9CA3AF]">{description}</p>}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-[#D1D5DB]">
          <thead className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
            <tr>
              <th className="pb-2">Parameter</th>
              <th className="pb-2">Type</th>
              <th className="pb-2">Required</th>
              <th className="pb-2">Default</th>
              <th className="pb-2">Description</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((entry) => (
              <tr key={entry.path} className="border-t border-[#1F2937]">
                <td className="py-3 font-semibold text-[#F3F4F6]">
                  <span
                    className="font-mono text-xs"
                    style={{ paddingLeft: entry.depth * 12 }}
                  >
                    {entry.path}
                  </span>
                </td>
                <td className="py-3 text-[#9CA3AF]">
                  <span className="font-mono text-xs">{entry.type}</span>
                </td>
                <td className="py-3 text-[#9CA3AF]">
                  {entry.required ? 'Yes' : 'No'}
                </td>
                <td className="py-3 text-[#9CA3AF]">
                  <span className="font-mono text-xs">{entry.defaultValue ?? '-'}</span>
                </td>
                <td className="py-3 text-[#D1D5DB]">{entry.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export type { ParameterEntry };
