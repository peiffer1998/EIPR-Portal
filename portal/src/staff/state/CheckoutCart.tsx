import React from "react";

export type CheckoutCartItem = {
  reservationId: string;
  ownerId: string;
  petName?: string;
  petId?: string;
  service?: string;
};

export type CheckoutCartState = {
  ownerId: string | null;
  items: CheckoutCartItem[];
};

const STORAGE_KEY = "eipr.checkout.cart";
const initialCart: CheckoutCartState = { ownerId: null, items: [] };

function loadCart(): CheckoutCartState {
  if (typeof window === "undefined") return initialCart;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return initialCart;
    const parsed = JSON.parse(raw);
    const ownerId = typeof parsed.ownerId === "string" ? parsed.ownerId : null;
    const items: CheckoutCartItem[] = Array.isArray(parsed.items)
      ? parsed.items
          .map((item: any): CheckoutCartItem | null => {
            const reservationId = String(item?.reservationId ?? item?.reservation_id ?? "").trim();
            const ownerIdItem = String(item?.ownerId ?? item?.owner_id ?? "").trim();
            if (!reservationId || !ownerIdItem) return null;
            return {
              reservationId,
              ownerId: ownerIdItem,
              petName: item?.petName ?? item?.pet_name ?? undefined,
              petId: item?.petId ?? item?.pet_id ?? undefined,
              service: item?.service ?? undefined,
            };
          })
          .filter(Boolean) as CheckoutCartItem[]
      : [];
    return { ownerId, items };
  } catch (error) {
    console.warn("checkout cart load failed", error);
    return initialCart;
  }
}

function persistCart(cart: CheckoutCartState) {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
  } catch (error) {
    console.warn("checkout cart save failed", error);
  }
}

export type CheckoutCartContextValue = {
  cart: CheckoutCartState;
  add: (item: CheckoutCartItem) => void;
  addMany: (items: CheckoutCartItem[]) => void;
  remove: (reservationId: string) => void;
  clear: () => void;
  count: number;
};

const CheckoutCartContext = React.createContext<CheckoutCartContextValue | null>(null);

export function CheckoutCartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = React.useState<CheckoutCartState>(() => loadCart());

  const commit = React.useCallback((next: CheckoutCartState) => {
    setCart(next);
    persistCart(next);
  }, []);

  const clear = React.useCallback(() => {
    commit(initialCart);
  }, [commit]);

  const add = React.useCallback(
    (item: CheckoutCartItem) => {
      if (!item.ownerId) {
        alert("Cannot add to checkout: reservation is missing an owner.");
        return;
      }

      if (cart.ownerId && cart.ownerId !== item.ownerId) {
        const replace = window.confirm("Checkout cart contains a different family. Replace with this family?");
        if (!replace) return;
        commit({ ownerId: item.ownerId, items: [item] });
        return;
      }

      const exists = cart.items.some((existing) => existing.reservationId === item.reservationId);
      if (exists) return;

      const ownerId = cart.ownerId ?? item.ownerId;
      commit({ ownerId, items: [...cart.items, item] });
    },
    [cart, commit],
  );

  const addMany = React.useCallback(
    (items: CheckoutCartItem[]) => {
      if (!items.length) return;
      const ownerId = items[0].ownerId;
      if (!ownerId) {
        alert("Cannot add to checkout: selected reservations are missing owner information.");
        return;
      }
      const mixedOwner = items.some((item) => item.ownerId !== ownerId);
      if (mixedOwner) {
        alert("Checkout cart can only contain one family at a time. Select dogs from the same family.");
        return;
      }

      if (cart.ownerId && cart.ownerId !== ownerId) {
        const replace = window.confirm("Checkout cart contains a different family. Replace with this family?");
        if (!replace) return;
        commit({ ownerId, items });
        return;
      }

      const existingIds = new Set(cart.items.map((item) => item.reservationId));
      const merged = [...cart.items];
      for (const item of items) {
        if (!existingIds.has(item.reservationId)) {
          merged.push(item);
        }
      }
      commit({ ownerId: cart.ownerId ?? ownerId, items: merged });
    },
    [cart, commit],
  );

  const remove = React.useCallback(
    (reservationId: string) => {
      const filtered = cart.items.filter((item) => item.reservationId !== reservationId);
      commit({ ownerId: filtered.length ? cart.ownerId ?? null : null, items: filtered });
    },
    [cart, commit],
  );

  const value = React.useMemo<CheckoutCartContextValue>(
    () => ({ cart, add, addMany, remove, clear, count: cart.items.length }),
    [cart, add, addMany, remove, clear],
  );

  return <CheckoutCartContext.Provider value={value}>{children}</CheckoutCartContext.Provider>;
}

export function useCheckoutCart(): CheckoutCartContextValue {
  const ctx = React.useContext(CheckoutCartContext);
  if (!ctx) throw new Error("useCheckoutCart must be used within CheckoutCartProvider");
  return ctx;
}
