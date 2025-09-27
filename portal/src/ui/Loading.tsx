export default function Loading({ text = 'Loading…' }: { text?: string }): JSX.Element {
  return <div className="p-4 text-sm text-slate-600">{text}</div>;
}
