import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import VirtualList from "../VirtualList";

describe("VirtualList", () => {
  it("renders a subset of items", () => {
    const items = Array.from({ length: 20 }, (_, index) => `Item ${index + 1}`);
    render(
      <VirtualList
        items={items}
        itemHeight={20}
        height={100}
        render={(item) => <div>{item}</div>}
      />,
    );

    expect(screen.getByText("Item 1")).toBeInTheDocument();
  });
});
