/**
 * Unit tests for AgentProvenancePanel — the Bean-0 provenance tab in the
 * agent detail view, wired to /api/agents/{name}/provenance (and the
 * optional /inference-receipts endpoint, which may 404).
 */
import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { AgentProvenancePanel } from "../AgentProvenancePanel";

const RECORD = {
  substrate: "silicon",
  framework: "smolagents",
  framework_ref: "v1.19.0",
  installer_sha256: "a".repeat(64),
  constitution_sha256: "b".repeat(64),
  model_id: "ollama/llama3",
  model_file_sha256: "c".repeat(64),
  corpus_refs: ["https://example.com/corpus.sqlbook", "local:corpus-1"],
  recorded_at: "2026-07-01T12:00:00Z",
};

const ENVELOPE = {
  agent_name: "scout",
  record: RECORD,
  constitution_sha256: RECORD.constitution_sha256,
  model_id: RECORD.model_id,
  recorded_at: 1751371200,
};

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  };
}

const originalFetch = global.fetch;
afterEach(() => {
  global.fetch = originalFetch;
  vi.clearAllMocks();
});

function stubFetch(handlers: {
  provenance: () => unknown;
  receipts?: () => unknown;
}) {
  global.fetch = vi.fn(async (url: unknown) => {
    const u = String(url);
    if (u.includes("/provenance")) return handlers.provenance();
    if (u.includes("/inference-receipts")) {
      if (handlers.receipts) return handlers.receipts();
      return jsonResponse({ error: "not found" }, 404);
    }
    return jsonResponse({}, 404);
  }) as unknown as typeof fetch;
}

describe("<AgentProvenancePanel />", () => {
  it("renders the provenance record fields", async () => {
    stubFetch({ provenance: () => jsonResponse(ENVELOPE) });
    render(<AgentProvenancePanel agentName="scout" />);

    await waitFor(() => expect(screen.getByText("silicon")).toBeInTheDocument());
    expect(screen.getByText("smolagents@v1.19.0")).toBeInTheDocument();
    expect(screen.getByText("ollama/llama3")).toBeInTheDocument();
    // Hashes shortened to 12 chars with full value in the title attribute.
    const constitution = screen.getByLabelText(`Copy constitution hash ${"b".repeat(64)}`);
    expect(constitution).toHaveTextContent(`${"b".repeat(12)}…`);
    expect(constitution).toHaveAttribute("title", "b".repeat(64));
    // Corpus refs: URLs as links, others as plain text.
    const link = screen.getByRole("link", { name: /example\.com\/corpus\.sqlbook/ });
    expect(link).toHaveAttribute("href", "https://example.com/corpus.sqlbook");
    expect(screen.getByText("local:corpus-1")).toBeInTheDocument();
  });

  it("accepts a bare record (no envelope) response", async () => {
    stubFetch({ provenance: () => jsonResponse(RECORD) });
    render(<AgentProvenancePanel agentName="scout" />);
    await waitFor(() =>
      expect(screen.getByText("smolagents@v1.19.0")).toBeInTheDocument()
    );
  });

  it("shows the quiet empty state on 404", async () => {
    stubFetch({ provenance: () => jsonResponse({ error: "nope" }, 404) });
    render(<AgentProvenancePanel agentName="scout" />);
    await waitFor(() =>
      expect(
        screen.getByText("No provenance recorded — Bean-0 not yet run for this agent")
      ).toBeInTheDocument()
    );
  });

  it("shows a receipts summary line when the receipts endpoint responds", async () => {
    stubFetch({
      provenance: () => jsonResponse(ENVELOPE),
      receipts: () =>
        jsonResponse({
          receipts: [
            { completed_at: "2026-07-20T10:00:00Z" },
            { completed_at: "2026-07-21T10:00:00Z" },
          ],
          count: 2,
        }),
    });
    render(<AgentProvenancePanel agentName="scout" />);
    await waitFor(() =>
      expect(screen.getByText(/2 inference receipts/)).toBeInTheDocument()
    );
  });

  it("omits the receipts line entirely when the receipts endpoint 404s", async () => {
    stubFetch({ provenance: () => jsonResponse(ENVELOPE) });
    render(<AgentProvenancePanel agentName="scout" />);
    await waitFor(() => expect(screen.getByText("silicon")).toBeInTheDocument());
    expect(screen.queryByText(/inference receipt/)).toBeNull();
  });
});
