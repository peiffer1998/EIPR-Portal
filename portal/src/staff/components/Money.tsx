export default function Money({ value }: { value: number | string }) {
  const numeric = typeof value === "string" ? Number(value) : value;
  const parsed = Number.isFinite(numeric) ? Number(numeric) : 0;
  return <span>${parsed.toFixed(2)}</span>;
}
