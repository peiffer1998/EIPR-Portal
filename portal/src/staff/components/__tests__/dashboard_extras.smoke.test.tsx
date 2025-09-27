import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import BatchBar from "../BatchBar";
import AlertsRail from "../AlertsRail";
import DrawerReservation from "../DrawerReservation";
import type { DashboardReservation } from "../../lib/dashboardFetchers";

vi.mock("../../lib/dashboardActions", () => ({
  listWaitlistOffered: vi.fn(async () => []),
  quickSms: vi.fn(async () => true),
  quickEmail: vi.fn(async () => true),
}));

vi.mock("../../lib/reservationOps", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("../../lib/reservationOps");
  return {
    ...actual,
    listRuns: vi.fn(async () => []),
    moveRun: vi.fn(async () => ({})),
    checkIn: vi.fn(async () => ({})),
    checkOut: vi.fn(async () => ({})),
  };
});

describe("dashboard extras", () => {
  it("renders batch bar actions", () => {
    render(
      <BatchBar
        count={2}
        onAddToCheckout={() => {}}
        onCheckIn={() => {}}
        onCheckOut={() => {}}
        onMoveRun={() => {}}
        onPrint={() => {}}
      />,
    );

    expect(screen.getByText(/2/)).toBeInTheDocument();
    expect(screen.getByText(/Check-In/)).toBeInTheDocument();
    expect(screen.getByText(/Move Run/)).toBeInTheDocument();
  });

  it("shows alert sections", async () => {
    const reservations: DashboardReservation[] = [
      {
        id: "res-1",
        reservation_type: "BOARDING",
        status: "CHECKED_IN",
        start_at: "2025-09-24T09:00:00Z",
        end_at: "2025-09-26T17:00:00Z",
        location_id: "loc-1",
        pet: { id: "pet-1", name: "Milo" },
        owner: { id: "own-1", first_name: "Ada", last_name: "Lovelace" },
        owner_id: "own-1",
        run_id: null,
        run_name: null,
        feeding_lines: [],
        medication_lines: [],
        vaccination_status: "expiring",
      },
      {
        id: "res-2",
        reservation_type: "BOARDING",
        status: "CHECKED_IN",
        start_at: "2025-09-20T09:00:00Z",
        end_at: "2025-09-21T12:00:00Z",
        location_id: "loc-1",
        pet: { id: "pet-2", name: "Nova" },
        owner: { id: "own-2", first_name: "Grace", last_name: "Hopper" },
        owner_id: "own-2",
        run_id: "run-3",
        run_name: "Run 3",
        feeding_lines: [],
        medication_lines: [],
        vaccination_status: "ok",
      },
    ];

    render(
      <AlertsRail
        dateISO="2025-09-27"
        locationId="loc-1"
        reservations={reservations}
        vaccineStates={{ "pet-1": "expiring", "pet-2": "ok" }}
        onFilter={() => {}}
      />,
    );

    expect(await screen.findByText(/Unassigned/)).toBeInTheDocument();
    expect(await screen.findByText(/Late Pickups/)).toBeInTheDocument();
    expect(await screen.findByText(/Vaccines Expiring/)).toBeInTheDocument();
  });

  it("does not render drawer when closed", () => {
    const { container } = render(
      <DrawerReservation reservation={null} onClose={() => {}} onRefresh={async () => {}} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
