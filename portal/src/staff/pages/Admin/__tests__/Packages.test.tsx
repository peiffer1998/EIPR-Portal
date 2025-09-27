import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import AdminPackages from "../Packages";

vi.mock("../../../lib/catalogFetchers", () => ({
  listPackageDefs: async () => [
    { id: "pkg1", name: "10 Daycare Days", credits: 10, credit_unit: "day", price: 200, active: true },
  ],
  listServiceItems: async () => [],
  createPackageDef: async () => ({}),
  updatePackageDef: async () => ({}),
  deletePackageDef: async () => ({}),
}));

const wrapper = (ui: React.ReactElement) => {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
};

describe("AdminPackages", () => {
  it("renders package definitions", async () => {
    render(wrapper(<AdminPackages />));
    expect(await screen.findByText(/10 Daycare Days/)).toBeInTheDocument();
  });
});
