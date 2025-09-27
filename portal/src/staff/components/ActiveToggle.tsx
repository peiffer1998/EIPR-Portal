interface Props {
  value?: boolean;
  onChange: (value: boolean) => Promise<void>;
}

export default function ActiveToggle({ value, onChange }: Props) {
  return (
    <label className="inline-flex items-center gap-2 text-sm">
      <input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} />
      <span>{value ? "Active" : "Inactive"}</span>
    </label>
  );
}
