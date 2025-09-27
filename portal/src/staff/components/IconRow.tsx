import { DoorOpen, Pill, Syringe, UtensilsCrossed } from "lucide-react";

export type VaccineState = "ok" | "expiring" | "expired" | "missing" | "unknown";

const VAX_COLORS: Record<VaccineState, string> = {
  ok: "text-emerald-600",
  expiring: "text-amber-500",
  expired: "text-red-600",
  missing: "text-red-600",
  unknown: "text-slate-300",
};

const VAX_LABELS: Record<VaccineState, string> = {
  ok: "Vaccinations current",
  expiring: "Vaccinations expiring soon",
  expired: "Vaccinations expired",
  missing: "Vaccinations missing",
  unknown: "Vaccination status unknown",
};

export default function IconRow({
  vaccineState = "unknown",
  hasMeds,
  hasFeeding,
  runLabel,
}: {
  vaccineState?: VaccineState;
  hasMeds?: boolean;
  hasFeeding?: boolean;
  runLabel?: string | null;
}) {
  const vaxState: VaccineState = vaccineState ?? "unknown";

  return (
    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
      <span className="inline-flex items-center gap-1" title={VAX_LABELS[vaxState]}>
        <Syringe size={14} className={VAX_COLORS[vaxState]} />
        <span className="hidden sm:inline">Vaccines</span>
      </span>
      {hasMeds ? (
        <span className="inline-flex items-center gap-1" title="Has medication schedule">
          <Pill size={14} className="text-purple-600" />
          <span className="hidden sm:inline">Meds</span>
        </span>
      ) : null}
      {hasFeeding ? (
        <span className="inline-flex items-center gap-1" title="Has feeding instructions">
          <UtensilsCrossed size={14} className="text-orange-500" />
          <span className="hidden sm:inline">Feeding</span>
        </span>
      ) : null}
      {runLabel ? (
        <span className="inline-flex items-center gap-1" title={`Run: ${runLabel}`}>
          <DoorOpen size={14} className="text-slate-600" />
          <span className="font-medium">{runLabel}</span>
        </span>
      ) : null}
    </div>
  );
}
