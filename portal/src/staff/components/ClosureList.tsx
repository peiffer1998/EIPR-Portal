interface Props {
  rows: Array<{ id?: string; start_date: string; end_date: string; reason?: string }>;
  onDelete: (id: string) => Promise<void>;
}

export default function ClosureList({ rows, onDelete }: Props) {
  return (
    <div className="bg-white rounded-xl shadow overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th className="px-3 py-2">Start</th>
            <th>End</th>
            <th>Reason</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id ?? `${row.start_date}-${row.end_date}`} className="border-t">
              <td className="px-3 py-2">{row.start_date.slice(0, 10)}</td>
              <td>{row.end_date.slice(0, 10)}</td>
              <td>{row.reason ?? ""}</td>
              <td>
                {row.id && (
                  <button
                    className="text-xs text-red-600"
                    type="button"
                    onClick={() => onDelete(row.id as string)}
                  >
                    Delete
                  </button>
                )}
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={4} className="px-3 py-4 text-sm text-slate-500">
                No closures
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
