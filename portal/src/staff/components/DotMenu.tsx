import React from "react";

export type DotMenuItem = {
  label: string;
  onClick: () => void;
  danger?: boolean;
  disabled?: boolean;
};

export default function DotMenu({ items }: { items: DotMenuItem[] }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (!ref.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        className="rounded-lg border border-slate-200 px-2 py-1 text-lg leading-none text-slate-600 transition hover:bg-slate-100"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
      >
        ⋯
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 z-30 mt-2 w-48 rounded-xl border border-slate-200 bg-white py-1 shadow-lg"
        >
          {items.map((item, index) => (
            <button
              key={`${item.label}-${index}`}
              type="button"
              role="menuitem"
              disabled={item.disabled}
              className={`block w-full px-3 py-2 text-left text-sm transition ${
                item.disabled
                  ? "cursor-not-allowed text-slate-300"
                  : item.danger
                  ? "text-red-600 hover:bg-red-50"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
              onClick={() => {
                setOpen(false);
                if (!item.disabled) {
                  item.onClick();
                }
              }}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
