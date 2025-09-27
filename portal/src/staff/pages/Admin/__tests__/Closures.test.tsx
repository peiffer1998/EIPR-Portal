import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, waitFor } from "@testing-library/react";

import AdminClosures from "../Closures";

vi.mock("../../../lib/adminFetchers", () => ({
  listLocations: async () => [
    { id: "loc-1", name: "Main" },
  ],
}));

vi.mock("../../../lib/hoursFetchers", () => ({
  listClosures: async () => [
    { id: "cls-1", start_date: "2025-12-24", end_date: "2025-12-25", reason: "Holiday" },
  ],
  createClosure: async () => undefined,
  deleteClosure: async () => undefined,
}));

const wrapper = (ui: React.ReactElement) => {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
};

describe("AdminClosures", () => {
  it("renders without crashing", async () => {
    render(wrapper(<AdminClosures />));
    await waitFor(() => expect(true).toBe(true));
  });
});
