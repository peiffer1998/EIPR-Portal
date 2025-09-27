import type { ReactNode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import ForecastMini from "../ForecastMini";
import { MemoryRouter } from "react-router-dom";

vi.mock("recharts", () => {
  const Container = ({ children }: { children?: ReactNode }) => <div>{children}</div>;
  const Leaf = () => null;
  return {
    ResponsiveContainer: Container,
    AreaChart: Container,
    Area: Leaf,
    XAxis: Leaf,
    YAxis: Leaf,
    Tooltip: Leaf,
    CartesianGrid: Leaf,
    BarChart: Container,
    Bar: Leaf,
    Legend: Leaf,
  };
});

const getBoardingAvailability = vi.fn();
const getDaycareCounts = vi.fn();
const getGroomingCounts = vi.fn();

vi.mock("../../lib/forecastFetchers", () => ({
  __esModule: true,
  getBoardingAvailability: (...args: Parameters<typeof getBoardingAvailability>) =>
    getBoardingAvailability(...args),
  getDaycareCounts: (...args: Parameters<typeof getDaycareCounts>) => getDaycareCounts(...args),
  getGroomingCounts: (...args: Parameters<typeof getGroomingCounts>) => getGroomingCounts(...args),
}));

describe("ForecastMini", () => {
  beforeEach(() => {
    getBoardingAvailability.mockReset().mockResolvedValue([
      { date: "2025-09-27", capacity: 20, booked: 12, available: 8 },
    ]);
    getDaycareCounts.mockReset().mockResolvedValue([{ date: "2025-09-27", count: 14 }]);
    getGroomingCounts.mockReset().mockResolvedValue([{ date: "2025-09-27", count: 6 }]);
  });

  it("loads forecast data for the next seven days", async () => {
    render(
      <MemoryRouter>
        <ForecastMini startISO="2025-09-27" />
      </MemoryRouter>,
    );

    await waitFor(() => expect(getBoardingAvailability).toHaveBeenCalled());

    expect(getBoardingAvailability).toHaveBeenCalledWith(undefined, "2025-09-27", 7);
    expect(getDaycareCounts).toHaveBeenCalledWith(undefined, "2025-09-27", 7);
    expect(getGroomingCounts).toHaveBeenCalledWith(undefined, "2025-09-27", 7);
    expect(screen.getByText(/Next 7 Days/i)).toBeInTheDocument();
    expect(screen.getByText(/Open Availability Report/i)).toHaveAttribute("href", "/staff/reports/availability");
  });
});
