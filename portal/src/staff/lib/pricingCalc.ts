import policy from "../../pricing/eipr_policy.json";

type QuoteRequest = {
  type: "daycare" | "boarding";
  nights?: number;
  days?: number;
  lodging?: "room" | "suite";
  dogs?: 1 | 2 | 3;
  daycare_with_boarding?: boolean;
  use_daycare_package?: boolean;
  fees?: { early?: boolean; late?: boolean; flea?: boolean };
};

type Line = {
  label: string;
  qty: number;
  unit: string;
  unit_price: number;
  amount: number;
};

type Quote = {
  lines: Line[];
  subtotal: number;
  discount_total: number;
  total: number;
  meta?: Record<string, unknown>;
};

const round2 = (n: number) => Math.round(n * 100) / 100;

export async function calcQuote(req: QuoteRequest): Promise<Quote> {
  const lines: Line[] = [];
  let subtotal = 0;
  let discountTarget = 0;
  let discount = 0;
  const meta: Record<string, unknown> = {};

  if (req.type === "daycare") {
    const days = Math.max(1, Math.floor(req.days ?? 1));
    if (req.use_daycare_package) {
      lines.push({
        label: "Daycare (package credit)",
        qty: days,
        unit: "day",
        unit_price: 0,
        amount: 0,
      });
      meta.packageCreditsUsed = days;
    } else {
      const price = policy.daycare.full_day_price;
      const amount = round2(days * price);
      lines.push({
        label: "Daycare Full Day",
        qty: days,
        unit: "day",
        unit_price: price,
        amount,
      });
      subtotal += amount;
    }
  }

  if (req.type === "boarding") {
    const nights = Math.max(1, Math.floor(req.nights ?? 1));
    const lodging = req.lodging ?? "room";
    const dogs = (req.dogs ?? 1) as 1 | 2 | 3;
    const nightlyMap = policy.boarding.nightly[lodging].dogs as Record<string, number>;
    const nightlyRate = nightlyMap[String(dogs)];

    const boardAmount = round2(nightlyRate * nights);
    lines.push({
      label: `Boarding ${lodging.charAt(0).toUpperCase()}${lodging.slice(1)} (${dogs} dog${dogs > 1 ? "s" : ""})`,
      qty: nights,
      unit: "night",
      unit_price: nightlyRate,
      amount: boardAmount,
    });
    subtotal += boardAmount;
    discountTarget += boardAmount;

    if (req.daycare_with_boarding) {
      const addon = policy.boarding.add_ons.daycare_per_day;
      const addAmount = round2(addon * nights);
      lines.push({
        label: "Daycare Add-On (per day)",
        qty: nights,
        unit: "day",
        unit_price: addon,
        amount: addAmount,
      });
      subtotal += addAmount;
    }

    if (req.fees?.early) {
      const fee = policy.boarding.add_ons.early_dropoff_fee;
      lines.push({ label: "Early Drop-off Fee", qty: 1, unit: "each", unit_price: fee, amount: fee });
      subtotal += fee;
    }
    if (req.fees?.late) {
      const fee = policy.boarding.add_ons.late_pickup_fee;
      lines.push({ label: "Late Pick-up Fee", qty: 1, unit: "each", unit_price: fee, amount: fee });
      subtotal += fee;
    }
    if (req.fees?.flea) {
      const fee = policy.boarding.add_ons.flea_treatment;
      lines.push({ label: "Flea Treatment", qty: 1, unit: "each", unit_price: fee, amount: fee });
      subtotal += fee;
    }

    const md = policy.boarding.multi_day_discount;
    if (nights > md.apply_after_nights && discountTarget > 0) {
      const percent = md.percent_off_boarding / 100;
      const discAmount = round2(discountTarget * percent);
      discount += discAmount;
      lines.push({
        label: `Multi-day discount (${md.percent_off_boarding}% after ${md.apply_after_nights} nights)`,
        qty: 1,
        unit: "each",
        unit_price: -discAmount,
        amount: -discAmount,
      });
    }
  }

  const total = round2(subtotal - discount);
  return {
    lines,
    subtotal: round2(subtotal),
    discount_total: round2(discount),
    total,
    meta,
  };
}

export type { Quote, QuoteRequest, Line };
