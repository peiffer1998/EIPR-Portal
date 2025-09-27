import { describe, expect, it } from "vitest";
import { calcQuote } from "../pricingCalc";

describe("pricingCalc", () => {
  it("applies 10% discount after sixth boarding night", async () => {
    const q = await calcQuote({ type: "boarding", nights: 7, lodging: "suite", dogs: 1 });
    expect(Number(q.subtotal.toFixed(2))).toBe(308.0);
    expect(Number(q.discount_total.toFixed(2))).toBe(30.8);
    expect(Number(q.total.toFixed(2))).toBe(277.2);
  });

  it("consumes package credit for daycare", async () => {
    const q = await calcQuote({ type: "daycare", days: 1, use_daycare_package: true });
    expect(q.total).toBe(0);
    expect(q.meta?.packageCreditsUsed).toBe(1);
  });

  it("boarding 3 nights room 1 dog totals $111", async () => {
    const q = await calcQuote({ type: 'boarding', nights: 3, lodging: 'room', dogs: 1 });
    expect(Number(q.total.toFixed(2))).toBe(111.0);
  });

  it("boarding 2 dogs room 2 nights totals $118", async () => {
    const q = await calcQuote({ type: 'boarding', nights: 2, lodging: 'room', dogs: 2 });
    expect(Number(q.total.toFixed(2))).toBe(118.0);
  });

  it("boarding with daycare add-on and fees", async () => {
    const q = await calcQuote({ type: 'boarding', nights: 2, lodging: 'suite', dogs: 1, daycare_with_boarding: true, fees: { early: true, late: true, flea: true } });
    expect(Number(q.total.toFixed(2))).toBe(44 * 2 + 15 * 2 + 10 + 20 + 15);
  });

});
