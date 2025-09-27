type Props = {
  value?: string | null;
  onClick?: (group: string | null) => void;
  active?: boolean;
};

const styles = {
  base: "px-2 py-1 rounded-full text-[11px] font-medium",
  ungrouped: "bg-slate-100 text-slate-700",
  small: "bg-blue-100 text-blue-800",
  large: "bg-green-100 text-green-800",
  other: "bg-purple-100 text-purple-800",
  active: "ring-2 ring-offset-1 ring-slate-400",
};

export default function GroupChip({ value, onClick, active = false }: Props) {
  const lower = value?.toLowerCase() || "";
  let palette = styles.other;
  if (!value) palette = styles.ungrouped;
  else if (lower.includes("small")) palette = styles.small;
  else if (lower.includes("large")) palette = styles.large;

  const className = [styles.base, palette, active ? styles.active : ""].filter(Boolean).join(" ");

  if (!onClick) return <span className={className}>{value || "Ungrouped"}</span>;
  return (
    <button type="button" className={className} onClick={() => onClick(value ?? null)}>
      {value || "Ungrouped"}
    </button>
  );
}
