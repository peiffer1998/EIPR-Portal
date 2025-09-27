import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import AdminInvitations from "../Invitations";

vi.mock("../../../lib/invitationsFetchers", () => ({
  listInvitations: async () => [
    { id: "i1", email: "alice@example.com", role: "STAFF", status: "pending", token: "tok" },
    { id: "i2", email: "bob@example.com", role: "MANAGER", status: "sent" },
  ],
  createInvitation: async () => ({ id: "new" }),
  resendInvitation: async () => undefined,
  revokeInvitation: async () => undefined,
}));

const wrapper = (ui: React.ReactElement) => {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
};

describe("AdminInvitations", () => {
  it("renders invitation rows", async () => {
    render(wrapper(<AdminInvitations />));
    expect(await screen.findByText("alice@example.com")).toBeInTheDocument();
    expect(await screen.findByText("bob@example.com")).toBeInTheDocument();
  });
});
