import api from "../../lib/api";
import policy from "../../pricing/eipr_policy.json";
import { calcQuote } from "./pricingCalc";
import type { QuoteRequest } from "./pricingCalc";

type QuoteResponse = Awaited<ReturnType<typeof calcQuote>>;

type ApiQuotePayload = QuoteRequest & { source?: "sandbox" };

type PushRulesResult = { pushed: boolean };

export async function tryApiQuote(payload: ApiQuotePayload): Promise<QuoteResponse | null> {
  try {
    const { data } = await api.post<QuoteResponse>('/pricing/quote', payload, { timeout: 5_000 });
    return data;
  } catch {
    return null;
  }
}

export async function getQuote(req: QuoteRequest): Promise<QuoteResponse> {
  const payload: ApiQuotePayload = { ...req, source: 'sandbox' };
  const apiQuote = await tryApiQuote(payload);
  if (apiQuote) return apiQuote;
  return calcQuote(req);
}

export async function pushRules(): Promise<PushRulesResult> {
  try {
    await api.post('/pricing/rules', policy, { timeout: 5_000 });
    return { pushed: true };
  } catch {
    return { pushed: false };
  }
}
