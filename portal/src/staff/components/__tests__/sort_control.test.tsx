import { fireEvent, render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import SortControl, { getStoredSort } from "../SortControl";

describe("SortControl", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("persists selection per tab", () => {
    const handleChange = vi.fn();

    const { rerender } = render(<SortControl tab="ARRIVING" value="start_asc" onChange={handleChange} />);

    fireEvent.change(screen.getByLabelText(/Sort/i), { target: { value: "pet_asc" } });

    expect(handleChange).toHaveBeenCalledWith("pet_asc");

    rerender(<SortControl tab="ARRIVING" value="pet_asc" onChange={handleChange} />);

    expect(window.localStorage.getItem("staff_dashboard_sort_ARRIVING")).toBe("pet_asc");
  });

  it("reads stored preference", () => {
    window.localStorage.setItem("staff_dashboard_sort_STAYING", "pet_asc");
    expect(getStoredSort("STAYING")).toBe("pet_asc");
  });
});
