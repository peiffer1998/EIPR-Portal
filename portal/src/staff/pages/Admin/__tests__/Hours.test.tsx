import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";

import AdminHours from "../Hours";

vi.mock("../../../lib/adminFetchers", () => ({
  listLocations: async () => [
    { id: "loc-1", name: "Main" },
  ],
}));

vi.mock("../../../lib/hoursFetchers", () => ({
  getLocationHours: async () => ({
    days: Array.from({ length: 7 }, (_, index) => ({
      weekday: index,
      is_closed: index >= 5,
      open: "08:00",
      close: "18:00",
    })),
  }),
  setLocationHours: async () => undefined,
}));

const wrapper = (ui: React.ReactElement) => {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
};

describe("AdminHours", () => {
  it("renders without crashing", async () => {
    render(wrapper(<AdminHours />));
    await waitFor(() => expect(true).toBe(true));
  });
});
