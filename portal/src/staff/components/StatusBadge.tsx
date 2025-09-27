const STATUS_CLASS: Record<string, string> = {
  GIVEN: "bg-green-100 text-green-800",
  DONE: "bg-green-100 text-green-800",
  SKIPPED: "bg-yellow-100 text-yellow-800",
  IN_PROGRESS: "bg-blue-100 text-blue-800",
  PENDING: "bg-slate-100 text-slate-700",
};

export default function StatusBadge({ status }: { status?: string }) {
  const normalized = status?.toUpperCase?.() || "PENDING";
  const cls = STATUS_CLASS[normalized] || "bg-slate-100 text-slate-700";
  return <span className={`px-2 py-1 rounded-full text-[11px] font-medium ${cls}`}>{normalized}</span>;
}
