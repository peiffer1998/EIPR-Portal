import api from "../../lib/api";

const ok = <T>(promise: Promise<{ data: T }>): Promise<T> => promise.then((response) => response.data);

export async function listPackages(params?: Record<string, unknown>) {
  try {
    return await ok<any[]>(api.get("/store/packages", { params }));
  } catch {
    return [];
  }
}

export async function sellPackage(ownerId: string, packageId: string, qty: number, priceOverride?: number) {
  try {
    return await ok<any>(
      api.post("/store/packages/sell", { owner_id: ownerId, package_id: packageId, qty, price_override: priceOverride }),
    );
  } catch {
    return ok<any>(api.post("/packages/sell", { owner_id: ownerId, package_id: packageId, qty, price_override: priceOverride }));
  }
}

export async function listOwnerPackages(ownerId: string) {
  try {
    return await ok<any[]>(api.get(`/owners/${ownerId}/packages`));
  } catch {
    return ok<any[]>(api.get("/packages", { params: { owner_id: ownerId, limit: 200 } }));
  }
}

export async function consumeOwnerPackage(ownerPackageId: string, amount: number) {
  try {
    return await ok<any>(api.post(`/store/packages/${ownerPackageId}/consume`, { amount }));
  } catch {
    return ok<any>(api.post(`/packages/${ownerPackageId}/consume`, { amount }));
  }
}

export async function listMemberships(params?: Record<string, unknown>) {
  try {
    return await ok<any[]>(api.get("/store/memberships", { params }));
  } catch {
    return [];
  }
}

export async function enrollMembership(ownerId: string, membershipId: string, startDate: string) {
  try {
    return await ok<any>(
      api.post("/store/memberships/enroll", { owner_id: ownerId, membership_id: membershipId, start_date: startDate }),
    );
  } catch {
    return ok<any>(api.post("/memberships/enroll", { owner_id: ownerId, membership_id: membershipId, start_date: startDate }));
  }
}

export async function listOwnerMemberships(ownerId: string) {
  try {
    return await ok<any[]>(api.get(`/owners/${ownerId}/memberships`));
  } catch {
    return ok<any[]>(api.get("/memberships", { params: { owner_id: ownerId, limit: 200 } }));
  }
}

export async function cancelOwnerMembership(ownerMembershipId: string) {
  try {
    return await ok<any>(api.post(`/store/memberships/${ownerMembershipId}/cancel`, {}));
  } catch {
    return ok<any>(api.post(`/memberships/${ownerMembershipId}/cancel`, {}));
  }
}

export async function listGifts(params?: Record<string, unknown>) {
  try {
    return await ok<any[]>(api.get("/store/gift-certificates", { params }));
  } catch {
    return [];
  }
}

export async function issueGift(amount: number, recipientOwnerId?: string) {
  try {
    return await ok<any>(api.post("/store/gift-certificates/issue", { amount, recipient_owner_id: recipientOwnerId }));
  } catch {
    return ok<any>(api.post("/gift-certificates/issue", { amount, recipient_owner_id: recipientOwnerId }));
  }
}

export async function redeemGift(code: string, ownerId: string) {
  try {
    return await ok<any>(api.post("/store/gift-certificates/redeem", { code, owner_id: ownerId }));
  } catch {
    return ok<any>(api.post("/gift-certificates/redeem", { code, owner_id: ownerId }));
  }
}

export async function getStoreCredit(ownerId: string) {
  try {
    return await ok<any>(api.get(`/owners/${ownerId}/store-credit`));
  } catch {
    return { owner_id: ownerId, balance: 0, ledger: [] };
  }
}

export async function addStoreCredit(ownerId: string, amount: number, note?: string) {
  try {
    return await ok<any>(api.post("/store/store-credit/add", { owner_id: ownerId, amount, note }));
  } catch {
    return ok<any>(api.post("/store-credit/add", { owner_id: ownerId, amount, note }));
  }
}

export async function applyCreditToInvoice(ownerId: string, invoiceId: string, amount: number) {
  try {
    return await ok<any>(api.post("/store/store-credit/apply", { owner_id: ownerId, invoice_id: invoiceId, amount }));
  } catch {
    return ok<any>(api.post(`/invoices/${invoiceId}/apply-credit`, { amount }));
  }
}

export async function getRewards(ownerId: string) {
  try {
    return await ok<any>(api.get(`/owners/${ownerId}/rewards`));
  } catch {
    return { owner_id: ownerId, points: 0, ledger: [] };
  }
}

export async function addPoints(ownerId: string, points: number, reason?: string) {
  try {
    return await ok<any>(api.post("/store/rewards/add", { owner_id: ownerId, points, reason }));
  } catch {
    return { ok: true };
  }
}

export async function redeemPoints(ownerId: string, points: number, reason?: string) {
  try {
    return await ok<any>(api.post("/store/rewards/redeem", { owner_id: ownerId, points, reason }));
  } catch {
    return { ok: true };
  }
}

export function rewardValueUSD(points: number, ratio = 0.01) {
  const pts = Number(points) || 0;
  const rate = Number(ratio) || 0;
  return Math.max(0, pts * rate);
}
