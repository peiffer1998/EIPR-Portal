import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ShoppingCart } from "lucide-react";

import { useCheckoutCart } from "../state/CheckoutCart";

export default function CheckoutButton(): JSX.Element | null {
  const navigate = useNavigate();
  const location = useLocation();
  const { count } = useCheckoutCart();

  const isStaffRoute = location.pathname.startsWith("/staff");
  if (!isStaffRoute) return null;

  return (
    <button
      type="button"
      onClick={() => navigate("/staff/checkout")}
      className="fixed right-4 top-4 z-[60] inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-lg transition hover:bg-slate-800"
      aria-label={`Open checkout cart, ${count} reservation${count === 1 ? "" : "s"}`}
    >
      <ShoppingCart size={18} />
      <span>Checkout</span>
      <span
        className={`ml-1 inline-flex min-w-[1.5rem] items-center justify-center rounded-full bg-orange-500 px-2 py-0.5 text-xs font-semibold ${
          count ? "" : "opacity-70"
        }`}
      >
        {count}
      </span>
    </button>
  );
}
