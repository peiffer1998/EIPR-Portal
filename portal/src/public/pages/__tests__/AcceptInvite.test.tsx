import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen } from "@testing-library/react";

import AcceptInvite from "../AcceptInvite";

vi.mock("../../../staff/lib/invitationsFetchers", () => ({
  acceptInvitation: async () => undefined,
}));

const wrapper = (path = "/invite/accept?token=abc") => {
  const client = new QueryClient();
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/invite/accept" element={<AcceptInvite />} />
          <Route path="/invite/accept/:token" element={<AcceptInvite />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe("AcceptInvite", () => {
  it("displays the accept invite form", async () => {
    render(wrapper());
    expect(await screen.findByText("Accept Invitation")).toBeInTheDocument();
  });
});
