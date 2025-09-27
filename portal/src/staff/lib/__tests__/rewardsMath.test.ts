import { describe, expect, it } from "vitest";

import { rewardValueUSD } from "../storeFetchers";

describe("rewardValueUSD", () => {
  it("defaults to 1¢ per point", () => {
    expect(rewardValueUSD(0)).toBe(0);
    expect(rewardValueUSD(100)).toBe(1);
  });

  it("supports custom ratios", () => {
    expect(rewardValueUSD(150, 0.02)).toBe(3);
  });
});
