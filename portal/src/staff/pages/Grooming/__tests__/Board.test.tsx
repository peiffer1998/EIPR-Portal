import type { ReactElement } from "react";
import { useEffect } from "react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import GroomingBoard from "../Board";

vi.mock("../../../components/GroomingFilters", () => {
  function MockGroomingFilters({ onChange }: { onChange: (filters: any) => void }) {
    useEffect(() => {
      onChange({ date: '2025-01-01', location_id: 'loc-1' });
    }, [onChange]);
    return <div data-testid="grooming-filters" />;
  }
  return { default: MockGroomingFilters };
});

vi.mock("../../../components/OwnerPicker", () => ({
  default: () => <div data-testid="owner-picker" />,
}));

vi.mock("../../../components/PetPicker", () => ({
  default: () => <div data-testid="pet-picker" />,
}));

vi.mock("../../../lib/groomingFetchers", () => ({
  getSpecialists: async () => [
    { id: "spec-1", name: "Ashley" },
    { id: "spec-2", name: "Sophia" },
  ],
  getServices: async () => [{ id: "svc-1", name: "Full Groom" }],
  getGroomingBoard: async () => [
    {
      id: "appt-1",
      specialist_id: "spec-1",
      start_at: new Date("2025-01-01T09:00:00").toISOString(),
      pet: { name: "Buddy" },
      owner: { first_name: "Alex", last_name: "Owner" },
      status: "BOOKED",
      service_name: "Full Groom",
    },
    {
      id: "appt-2",
      specialist_id: "spec-2",
      start_at: new Date("2025-01-01T10:00:00").toISOString(),
      pet: { name: "Zoe" },
      owner: { first_name: "Billie", last_name: "Parent" },
      status: "BOOKED",
      service_name: "Bath",
    },
  ],
  rescheduleAppointment: async () => ({}),
  setAppointmentStatus: async () => ({}),
  createAppointment: async () => ({ id: "new" }),
  getAppointment: async () => ({ id: "appt-1" }),
}));

const wrap = (ui: ReactElement) => {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
};

describe("GroomingBoard", () => {
  it("renders specialists and appointments", async () => {
    render(wrap(<GroomingBoard />));

    expect(await screen.findByText("Ashley")).toBeInTheDocument();
    expect(await screen.findByText("Sophia")).toBeInTheDocument();
    expect(await screen.findByText(/Buddy/)).toBeInTheDocument();
    expect(await screen.findByText(/Zoe/)).toBeInTheDocument();
  });
});
