import React from "react";

type VirtualListProps<T> = {
  items: T[];
  itemHeight: number;
  height: number;
  overscan?: number;
  focusIndex?: number | null;
  render: (item: T, index: number, isFocused: boolean) => React.ReactNode;
};

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

export default function VirtualList<T>({
  items,
  itemHeight,
  height,
  overscan = 4,
  focusIndex = null,
  render,
}: VirtualListProps<T>): JSX.Element {
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = React.useState(0);

  React.useEffect(() => {
    if (focusIndex == null) return;
    const container = scrollRef.current;
    if (!container) return;
    const itemTop = focusIndex * itemHeight;
    const itemBottom = itemTop + itemHeight;
    const viewTop = container.scrollTop;
    const viewBottom = viewTop + height;

    if (itemTop < viewTop) {
      container.scrollTop = itemTop;
    } else if (itemBottom > viewBottom) {
      container.scrollTop = itemBottom - height;
    }
  }, [focusIndex, itemHeight, height]);

  const totalHeight = items.length * itemHeight;
  const startIndex = clamp(Math.floor(scrollTop / itemHeight) - overscan, 0, Math.max(items.length - 1, 0));
  const endIndex = clamp(Math.ceil((scrollTop + height) / itemHeight) + overscan, 0, items.length);

  const visibleItems = items.slice(startIndex, endIndex);

  return (
    <div
      ref={scrollRef}
      className="overflow-auto"
      style={{ height }}
      onScroll={(event) => setScrollTop((event.target as HTMLDivElement).scrollTop)}
    >
      <div style={{ height: totalHeight, position: "relative" }}>
        <div
          style={{
            position: "absolute",
            top: startIndex * itemHeight,
            left: 0,
            right: 0,
          }}
        >
          {visibleItems.map((item, offset) => {
            const index = startIndex + offset;
            return (
              <div key={index} style={{ height: itemHeight }}>
                {render(item, index, focusIndex === index)}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
