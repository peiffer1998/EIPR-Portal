import type { ReactNode } from "react";

type Column = {
  key: string;
  label: string;
  align?: "left" | "right";
};

type Props = {
  rows: Array<{ id?: string | number } & Record<string, ReactNode>>;
  columns: Column[];
};

export default function LedgerTable({ rows, columns }: Props) {
  const data = rows ?? [];

  return (
    <div className="overflow-auto rounded-xl bg-white shadow">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-500">
            {columns.map((column) => (
              <th
                key={column.key}
                className={`px-3 py-2 text-left ${column.align === "right" ? "text-right" : ""}`}
              >
                {column.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, index) => (
            <tr key={row.id ?? index} className="border-t">
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`px-3 py-2 ${column.align === "right" ? "text-right" : ""}`}
                >
                  {row[column.key] ?? ""}
                </td>
              ))}
            </tr>
          ))}
          {data.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-3 py-4 text-sm text-slate-500">
                No entries
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
