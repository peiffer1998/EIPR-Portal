import { describe, expect, it } from "vitest";

import { computeTotals } from "../billingFetchers";

describe("computeTotals", () => {
  it("calculates subtotal, discount, tax, and total correctly", () => {
    const totals = computeTotals(
      [
        { description: "Boarding", qty: 2, unit_price: 50, taxable: true },
        { description: "Bath", qty: 1, unit_price: 25, taxable: false },
      ],
      10,
      0.07,
    );

    expect(totals.subtotal).toBe(125);
    expect(totals.discount).toBe(10);
    expect(totals.tax).toBeCloseTo(6.3, 2);
    expect(totals.total).toBeCloseTo(121.3, 2);
  });
});
