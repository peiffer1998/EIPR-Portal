import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PrintLayout from "../PrintLayout";

describe("PrintLayout", () => {
  it("renders title and meta values", () => {
    render(
      <PrintLayout title="Test Document" meta={[{ label: "ID", value: "abc" }]}> 
        <div>Body content</div>
      </PrintLayout>,
    );

    expect(screen.getByText("Test Document")).toBeInTheDocument();
    expect(screen.getByText(/ID/)).toBeInTheDocument();
    expect(screen.getByText("Body content")).toBeInTheDocument();
  });
});
