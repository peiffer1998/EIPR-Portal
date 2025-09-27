import { describe, expect, it } from "vitest";
import { getSelectedIds, initialSelection, selectionReducer } from "../rosterState";

describe("selectionReducer", () => {
  it("toggles ids", () => {
    let state = initialSelection;
    state = selectionReducer(state, { type: "toggle", id: "a" });
    expect(state).toEqual({ a: true });
    state = selectionReducer(state, { type: "toggle", id: "a" });
    expect(state).toEqual({ a: false });
  });

  it("replaces state", () => {
    const state = selectionReducer(initialSelection, {
      type: "replace",
      next: { a: true, b: true },
    });
    expect(getSelectedIds(state)).toEqual(["a", "b"]);
  });

  it("clears state", () => {
    const populated = { a: true };
    const state = selectionReducer(populated, { type: "clear" });
    expect(state).toEqual({});
  });
});
