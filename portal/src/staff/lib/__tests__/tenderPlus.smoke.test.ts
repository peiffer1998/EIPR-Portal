import { describe, it, expect } from "vitest";

import { isLateReservation } from "../tenderPlus";

describe("tenderPlus helpers", () => {
  it("detects late reservations", () => {
    expect(
      isLateReservation({
        end_at: new Date(Date.now() - 60_000).toISOString(),
        status: "CHECKED_IN",
      } as any),
    ).toBe(true);
  });
});
