import type { FormEvent } from "react";

type Field = {
  name: string;
  label: string;
  type?: string;
  placeholder?: string;
};

type Props = {
  title: string;
  fields: Field[];
  onSubmit: (values: Record<string, string>) => Promise<void>;
  submitLabel?: string;
};

export default function SmallForm({ title, fields, onSubmit, submitLabel = "Save" }: Props) {
  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const payload: Record<string, string> = {};
    fields.forEach((field) => {
      const value = formData.get(field.name);
      payload[field.name] = typeof value === "string" ? value : "";
    });
    await onSubmit(payload);
    form.reset();
  };

  return (
    <form className="grid items-end gap-2 rounded-xl bg-white p-4 shadow md:grid-cols-3" onSubmit={handleSubmit}>
      <div className="md:col-span-3 text-sm font-semibold text-slate-700">{title}</div>
      {fields.map((field) => (
        <label key={field.name} className="grid text-sm">
          <span className="text-slate-600">{field.label}</span>
          <input
            className="border rounded px-3 py-2"
            name={field.name}
            type={field.type || "text"}
            placeholder={field.placeholder || ""}
          />
        </label>
      ))}
      <div className="md:col-span-3">
        <button type="submit" className="rounded bg-slate-900 px-3 py-2 text-white">
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
