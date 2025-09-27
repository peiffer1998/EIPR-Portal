import React from "react";

function formatTime(value?: Date | null): string {
  if (!value) return "—";
  return value.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' });
}

export default function LiveIndicator({ lastUpdated }: { lastUpdated?: Date | null }): JSX.Element {
  return (
    <div className="flex items-center gap-2 text-xs text-slate-500">
      <span
        className="inline-flex h-2 w-2 animate-pulse rounded-full bg-emerald-500"
        title="Auto refresh active"
        aria-hidden
      />
      <span>Live · {formatTime(lastUpdated)}</span>
    </div>
  );
}
