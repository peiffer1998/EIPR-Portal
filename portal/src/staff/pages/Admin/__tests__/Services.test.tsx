import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import AdminServices from "../Services";

vi.mock("../../../lib/catalogFetchers", () => ({
  listServiceItems: async () => [
    { id: "svc1", name: "Bath", duration_min: 60, price: 25, active: true },
  ],
  createServiceItem: async () => ({}),
  updateServiceItem: async () => ({}),
  deleteServiceItem: async () => ({}),
}));

const wrapper = (ui: React.ReactElement) => {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
};

describe("AdminServices", () => {
  it("renders fetched service rows", async () => {
    render(wrapper(<AdminServices />));
    expect(await screen.findByText("Bath")).toBeInTheDocument();
  });
});
