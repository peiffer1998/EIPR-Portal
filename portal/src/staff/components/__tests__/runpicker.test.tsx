import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

import RunPickerModal from "../RunPickerModal";

type RunRecord = { id: string; name?: string | null; capacity?: number | null };

const listRunsMock = vi.fn<[string | undefined], Promise<RunRecord[]>>();

vi.mock("../../lib/reservationOps", () => ({
  listRuns: (locationId?: string) => listRunsMock(locationId),
}));

describe("RunPickerModal", () => {
  beforeEach(() => {
    listRunsMock.mockResolvedValue([
      { id: "run-1", name: "North Suite", capacity: 4 },
      { id: "run-2", name: "South Suite", capacity: 3 },
    ]);
  });

  it("loads runs and reports occupancy", async () => {
    const onPick = vi.fn();
    const onClose = vi.fn();

    render(
      <RunPickerModal
        open
        locationId="loc-1"
        currentRunId="run-2"
        occupancy={{ "run-1": 2, "run-2": 1 }}
        onPick={onPick}
        onClose={onClose}
      />,
    );

    await waitFor(() => expect(screen.getByText("North Suite")).toBeInTheDocument());
    expect(listRunsMock).toHaveBeenCalledWith("loc-1");
    expect(screen.getByText(/2 \/ 4/)).toBeInTheDocument();
    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();

    fireEvent.click(screen.getByText("North Suite"));
    expect(onPick).toHaveBeenCalledWith("run-1");
  });

  it("allows unassigning a run", async () => {
    const onPick = vi.fn();
    const onClose = vi.fn();

    render(
      <RunPickerModal
        open
        currentRunId="run-1"
        occupancy={{}}
        onPick={onPick}
        onClose={onClose}
      />,
    );

    await waitFor(() => expect(screen.getByText("North Suite")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Unassigned"));
    expect(onPick).toHaveBeenCalledWith(null);
  });

  it("filters runs by query", async () => {
    const onPick = vi.fn();
    const onClose = vi.fn();

    render(
      <RunPickerModal
        open
        occupancy={{}}
        onPick={onPick}
        onClose={onClose}
      />,
    );

    await waitFor(() => expect(screen.getByText("North Suite")).toBeInTheDocument());

    fireEvent.change(screen.getByPlaceholderText(/run name/i), {
      target: { value: "south" },
    });

    expect(screen.queryByText("North Suite")).not.toBeInTheDocument();
    expect(screen.getByText("South Suite")).toBeInTheDocument();
  });
});
