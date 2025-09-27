export type SelectionState = Record<string, boolean>;

export type SelectionAction =
  | { type: "toggle"; id: string }
  | { type: "set"; id: string; value: boolean }
  | { type: "replace"; next: SelectionState }
  | { type: "clear" };

export function selectionReducer(state: SelectionState, action: SelectionAction): SelectionState {
  switch (action.type) {
    case "toggle": {
      const next = { ...state };
      next[action.id] = !next[action.id];
      return next;
    }
    case "set": {
      if (state[action.id] === action.value) return state;
      return { ...state, [action.id]: action.value };
    }
    case "replace":
      return { ...action.next };
    case "clear":
      if (Object.keys(state).length === 0) return state;
      return {};
    default:
      return state;
  }
}

export const initialSelection: SelectionState = {};

export const getSelectedIds = (state: SelectionState): string[] =>
  Object.entries(state)
    .filter(([, value]) => Boolean(value))
    .map(([id]) => id);
