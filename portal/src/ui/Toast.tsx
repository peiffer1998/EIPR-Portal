import { useEffect, useState } from "react";

type ToastItem = {
  id: string;
  text: string;
  kind?: "info" | "error" | "success";
  ttl?: number;
};

const subscribers: Array<(toast: ToastItem) => void> = [];

export function toast(text: string, kind: ToastItem["kind"] = "info", ttl = 6000): void {
  const id = Math.random().toString(36).slice(2);
  subscribers.forEach((fn) => fn({ id, text, kind, ttl }));
}

export default function ToastHost(): JSX.Element {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    const handler = (item: ToastItem) => {
      setItems((current) => [...current, item]);
      setTimeout(() => {
        setItems((current) => current.filter((toast) => toast.id !== item.id));
      }, item.ttl ?? 6000);
    };

    subscribers.push(handler);
    return () => {
      const index = subscribers.indexOf(handler);
      if (index >= 0) subscribers.splice(index, 1);
    };
  }, []);

  return (
    <div
      aria-live="assertive"
      className="no-print fixed right-3 bottom-3 z-[9999] flex flex-col gap-2"
    >
      {items.map((item) => (
        <div
          key={item.id}
          className={`px-3 py-2 rounded text-sm shadow ${
            item.kind === "error"
              ? "bg-red-600 text-white"
              : item.kind === "success"
                ? "bg-green-600 text-white"
                : "bg-slate-900 text-white"
          }`}
        >
          {item.text}
        </div>
      ))}
    </div>
  );
}
