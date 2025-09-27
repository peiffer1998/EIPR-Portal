import { useRef } from "react";

interface Props {
  onCreate: (values: { start_date: string; end_date: string; reason?: string }) => Promise<void>;
}

export default function ClosureForm({ onCreate }: Props) {
  const formRef = useRef<HTMLFormElement>(null);

  return (
    <form
      ref={formRef}
      className="bg-white p-4 rounded-xl shadow grid md:grid-cols-4 gap-2 items-end"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!formRef.current) return;
        const data = new FormData(formRef.current);
        const start = String(data.get("start_date") || "");
        const end = String(data.get("end_date") || "");
        const reason = String(data.get("reason") || "").trim();
        if (!start || !end) return;
        await onCreate({ start_date: start, end_date: end, reason: reason || undefined });
        formRef.current.reset();
      }}
    >
      <label className="text-sm grid">
        <span>Start date</span>
        <input className="border rounded px-3 py-2" type="date" name="start_date" />
      </label>
      <label className="text-sm grid">
        <span>End date</span>
        <input className="border rounded px-3 py-2" type="date" name="end_date" />
      </label>
      <label className="text-sm grid md:col-span-2">
        <span>Reason</span>
        <input
          className="border rounded px-3 py-2"
          type="text"
          name="reason"
          placeholder="Holiday, maintenance, etc."
        />
      </label>
      <div className="md:col-span-4 flex justify-end">
        <button className="px-3 py-2 rounded bg-slate-900 text-white" type="submit">
          Add closure
        </button>
      </div>
    </form>
  );
}
