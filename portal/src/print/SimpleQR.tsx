import React from "react";

function hash(value: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < value.length; i += 1) {
    h ^= value.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
    h >>>= 0;
  }
  return h;
}

export default function SimpleQR({ value, size = 64, cells = 8 }: {
  value: string;
  size?: number;
  cells?: number;
}) {
  const safeValue = value || "";
  const code = hash(safeValue);
  const cell = Math.max(2, Math.floor(size / cells));
  const squares: JSX.Element[] = [];

  for (let idx = 0; idx < cells * cells; idx += 1) {
    const seed = (code ^ (idx * 0x9e3779b9)) >>> 0;
    if ((seed & 1) === 1) {
      const x = (idx % cells) * cell;
      const y = Math.floor(idx / cells) * cell;
      squares.push(
        <rect
          key={idx}
          x={x}
          y={y}
          width={cell}
          height={cell}
          fill="#0f172a"
        />
      );
    }
  }

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${cell * cells} ${cell * cells}`}
      role="img"
      aria-label={`Lookup code ${safeValue}`}
    >
      <rect x={0} y={0} width={cell * cells} height={cell * cells} fill="#fff" />
      {squares}
    </svg>
  );
}
