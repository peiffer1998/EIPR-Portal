import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import SkipToContent from "../SkipToContent";

describe("SkipToContent", () => {
  it("renders a skip link", () => {
    render(<SkipToContent />);
    expect(screen.getByText("Skip to main content")).toHaveAttribute("href", "#main");
  });
});
