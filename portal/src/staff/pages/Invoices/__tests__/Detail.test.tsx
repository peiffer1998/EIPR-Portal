import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen } from "@testing-library/react";

import InvoiceDetail from "../Detail";

vi.mock("../../../lib/billingFetchers", async () => {
  const actual = await vi.importActual<typeof import("../../../lib/billingFetchers")>("../../../lib/billingFetchers");
  return {
    ...actual,
    getInvoice: async (id: string) => ({
      id,
      status: "PENDING",
      lines: [
        { id: "l1", description: "Boarding", qty: 2, unit_price: 50, taxable: true },
      ],
      discount_total: 0,
      tax_total: 0,
      subtotal: 100,
      total: 100,
      payments: [],
    }),
    addLine: async () => ({}),
    updateLine: async () => ({}),
    removeLine: async () => ({}),
    setDiscount: async () => ({}),
    setTaxes: async () => ({}),
    finalizeInvoice: async () => ({}),
    emailReceipt: async () => ({}),
    applyStoreCredit: async () => ({}),
    capturePayment: async () => ({}),
    refundPayment: async () => ({}),
  };
});

const renderWithRouter = (invoiceId = "inv-1") => {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/staff/invoices/${invoiceId}`]}>
        <Routes>
          <Route path="/staff/invoices/:invoiceId" element={<InvoiceDetail />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe("InvoiceDetail", () => {
  it("renders invoice header and line items", async () => {
    renderWithRouter();

    expect(await screen.findByText(/Invoice inv-1/)).toBeInTheDocument();
    expect(await screen.findByDisplayValue("Boarding")).toBeInTheDocument();
  });
});
