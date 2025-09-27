import { useState } from "react";

interface Props {
  onChange: (query: string) => void;
  placeholder?: string;
}

export default function SearchBox({ onChange, placeholder = "Search…" }: Props) {
  const [query, setQuery] = useState("");

  return (
    <input
      className="border rounded px-3 py-2 w-full md:w-[320px]"
      value={query}
      placeholder={placeholder}
      onChange={(event) => {
        const next = event.target.value;
        setQuery(next);
        onChange(next);
      }}
    />
  );
}
