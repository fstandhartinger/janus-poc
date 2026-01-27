interface ConfigEntry {
  name: string;
  description: string;
  defaultValue?: string;
}

interface ConfigTableProps {
  title?: string;
  description?: string;
  entries: ConfigEntry[];
  className?: string;
}

export function ConfigTable({ title, description, entries, className }: ConfigTableProps) {
  return (
    <div className={`glass-card p-6 space-y-4 ${className ?? ''}`.trim()}>
      {(title || description) && (
        <div className="space-y-2">
          {title && (
            <h3 className="text-lg font-semibold text-[#F3F4F6]">{title}</h3>
          )}
          {description && (
            <p className="text-sm text-[#9CA3AF]">{description}</p>
          )}
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-[#D1D5DB]">
          <thead className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
            <tr>
              <th className="pb-2">Variable</th>
              <th className="pb-2">Default</th>
              <th className="pb-2">Description</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => (
              <tr key={entry.name} className="border-t border-[#1F2937]">
                <td className="py-3 font-semibold text-[#F3F4F6]">
                  <span className="font-mono text-xs">{entry.name}</span>
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

export type { ConfigEntry };
