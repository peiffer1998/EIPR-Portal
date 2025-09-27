import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";

import FilesPage from "../Files";

vi.mock("../../../lib/documentsFetchers", () => ({
  listDocuments: async () => [
    { id: "doc-1", name: "health.pdf", mime: "application/pdf", size_bytes: 1024, status: "uploaded" },
  ],
  uploadDocument: async () => ({ id: "new" }),
  finalizeDocument: async () => ({ ok: true }),
  deleteDocument: async () => true,
  fetchDocumentBlob: async () => new Blob(["hi"], { type: "text/plain" }),
  buildDocumentLink: (id: string) => `/api/v1/documents/${id}`,
}));

const wrapper = (ui: React.ReactElement) => {
  const client = new QueryClient();
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
};

describe("FilesPage", () => {
  it("renders document rows", async () => {
    render(wrapper(<FilesPage />));
    expect(await screen.findByText("health.pdf")).toBeInTheDocument();
  });
});
