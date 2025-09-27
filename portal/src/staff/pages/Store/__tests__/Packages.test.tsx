import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import StorePackages from "../Packages";

vi.mock("../../../lib/storeFetchers", () => ({
  listPackages: async () => [{ id: "pkg1", name: "10 Daycare Days", qty: 10, price: 200 }],
  listOwnerPackages: async () => [{ id: "op1", package_name: "10 Daycare Days", remaining: 5, status: "ACTIVE" }],
  sellPackage: async () => ({}),
  consumeOwnerPackage: async () => ({}),
}));

const renderWithClient = (component: React.ReactElement) => {
  const client = new QueryClient();
  return render(<QueryClientProvider client={client}>{component}</QueryClientProvider>);
};

describe("StorePackages", () => {
  it("renders available packages", async () => {
    renderWithClient(<StorePackages />);
    expect(await screen.findByText(/10 Daycare Days/)).toBeInTheDocument();
  });
});
