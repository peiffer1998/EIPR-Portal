import { useEffect, useRef } from "react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const daycareMocks = vi.hoisted(() => ({
  mockGetDaycareRoster: vi.fn(async () => ([
    {
      id: "r1",
      pet: { name: "Buddy" },
      owner: { first_name: "Ann", last_name: "Owner" },
      program: "Standard",
      group: null,
      status: "REQUESTED",
      check_in_at: null,
      check_out_at: null,
      location_id: "loc-1",
      late_pickup: false,
      standing: true,
    },
    {
      id: "r2",
      pet: { name: "Zoe" },
      owner: { first_name: "Ben", last_name: "Parent" },
      program: "Full-Day",
      group: "Small Dogs",
      status: "CHECKED_IN",
      check_in_at: "08:00",
      check_out_at: null,
      location_id: "loc-1",
      late_pickup: true,
      standing: false,
    },
  ])),
  mockCheckIn: vi.fn(async () => ({})),
  mockCheckOut: vi.fn(async () => ({})),
  mockAssignGroup: vi.fn(async () => ({})),
  mockLogIncident: vi.fn(async () => ({})),
}));

vi.mock("../../../components/BoardFilters", () => {
  const BoardFiltersMock = ({ onChange }: { onChange: (filters: { date: string; location_id: string }) => void }) => {
    const called = useRef(false);
    useEffect(() => {
      if (called.current) return;
      onChange({ date: "2025-01-01", location_id: "loc-1" });
      called.current = true;
    }, [onChange]);
    return <div data-testid="board-filters" />;
  };
  return { default: BoardFiltersMock };
});

vi.mock("../../../components/ProgramSelect", () => ({
  default: ({ onChange }: { onChange: (value: string) => void }) => (
    <button onClick={() => onChange("Standard")} data-testid="program-select">
      ProgramSelect
    </button>
  ),
}));

vi.mock("../../../components/IncidentDialog", () => ({
  default: () => null,
}));

vi.mock("../../../lib/daycareFetchers", () => ({
  getDaycareRoster: daycareMocks.mockGetDaycareRoster,
  checkIn: daycareMocks.mockCheckIn,
  checkOut: daycareMocks.mockCheckOut,
  assignGroup: daycareMocks.mockAssignGroup,
  logIncident: daycareMocks.mockLogIncident,
  listPrograms: async () => ["Standard", "Full-Day"],
}));

const { mockCheckIn, mockCheckOut, mockAssignGroup, mockLogIncident } = daycareMocks;

type DaycareRosterComponent = (typeof import("../Roster"))["default"];
let DaycareRoster: DaycareRosterComponent;
beforeAll(async () => {
  DaycareRoster = (await import("../Roster")).default;
});

afterEach(() => {
  mockCheckIn.mockClear();
  mockCheckOut.mockClear();
  mockAssignGroup.mockClear();
  mockLogIncident.mockClear();
});

function renderRoster() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <DaycareRoster />
    </QueryClientProvider>,
  );
}

describe("DaycareRoster", () => {
  it("renders roster rows and standing hint", async () => {
    renderRoster();
    expect(await screen.findByText("Buddy")).toBeInTheDocument();
    expect(screen.getByText("Zoe")).toBeInTheDocument();
    const standingBadges = await screen.findAllByText(/Standing reservation/);
    expect(standingBadges.length).toBeGreaterThan(0);
  });

  it("performs bulk check-out", async () => {
    const user = userEvent.setup();
    renderRoster();

    await waitFor(() => expect(screen.getAllByRole("checkbox").length).toBeGreaterThan(1));
    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[1]);
    expect((checkboxes[1] as HTMLInputElement).checked).toBe(true);
    const [bulkButton] = await screen.findAllByText("Bulk Check-Out");
    await user.click(bulkButton);

    await waitFor(() => expect(mockCheckOut).toHaveBeenCalledTimes(1));
  });
});
