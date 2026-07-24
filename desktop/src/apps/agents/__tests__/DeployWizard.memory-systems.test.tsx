/**
 * Track 2 (memory-systems-integration.md): the memory-systems multi-select
 * added to MemoryWizardStep. Verifies the three checkboxes render (taosmd
 * checked + disabled, tmrfs/pk-trust toggleable) and that toggling tmrfs
 * reports it back to the parent's memorySystems array — the array that
 * DeployWizard.handleDeploy threads into the deploy POST body as
 * `memory_systems: string[]`.
 */
import { useState } from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { MemoryWizardStep, type MemoryWizardStepProps } from "../DeployWizard";

const originalFetch = global.fetch;
afterEach(() => {
  global.fetch = originalFetch;
  vi.clearAllMocks();
});

function stubFetch() {
  // MemoryWizardStep fetches /api/taosmd/default and /api/cluster/install-targets
  // on mount. Neither response matters here since memoryDefault/memoryPlugin
  // are passed in directly ("has default" mode), but the calls must not throw.
  global.fetch = vi.fn(async () => ({
    ok: true,
    status: 200,
    headers: { get: () => "application/json" },
    json: async () => ({}),
  })) as unknown as typeof fetch;
}

/** Wrapper that owns memorySystems state so toggling re-renders like the real wizard. */
function Wrapper() {
  const [memorySystems, setMemorySystems] = useState<string[]>(["taosmd"]);

  const props: MemoryWizardStepProps = {
    memoryPlugin: "taosmd",
    setMemoryPlugin: vi.fn(),
    memoryDeviceId: null,
    setMemoryDeviceId: vi.fn(),
    memoryTierId: null,
    setMemoryTierId: vi.fn(),
    memoryDefault: { device_id: "dev1", tier_id: "standard", tier_name: "Standard" },
    setMemoryDefault: vi.fn(),
    memoryInstallTargets: [],
    setMemoryInstallTargets: vi.fn(),
    memoryDevicesLoaded: true,
    setMemoryDevicesLoaded: vi.fn(),
    memorySetupTaskId: null,
    setMemorySetupTaskId: vi.fn(),
    memorySetupState: "pending",
    setMemorySetupState: vi.fn(),
    memorySetupMsg: "",
    setMemorySetupMsg: vi.fn(),
    memorySetupError: null,
    setMemorySetupError: vi.fn(),
    memoryPickerMode: "default",
    setMemoryPickerMode: vi.fn(),
    memorySystems,
    setMemorySystems,
  };

  return (
    <div>
      <MemoryWizardStep {...props} />
      {/* Surface current selection for assertions without reaching into React internals. */}
      <div data-testid="current-selection">{memorySystems.join(",")}</div>
    </div>
  );
}

describe("<MemoryWizardStep /> memory-systems selector", () => {
  it("renders taosmd checked+disabled and tmrfs/pk-trust toggleable, unchecked by default", () => {
    stubFetch();
    render(<Wrapper />);

    const taosmd = screen.getByRole("checkbox", { name: /taosmd/i });
    expect(taosmd).toBeChecked();
    expect(taosmd).toBeDisabled();
    expect(screen.getByText("Conversational memory (always on)")).toBeInTheDocument();

    const tmrfs = screen.getByRole("checkbox", { name: /tmrfs/i });
    const pkTrust = screen.getByRole("checkbox", { name: /pk-trust/i });
    expect(tmrfs).not.toBeChecked();
    expect(tmrfs).not.toBeDisabled();
    expect(pkTrust).not.toBeChecked();
    expect(pkTrust).not.toBeDisabled();

    expect(
      screen.getByText(/Tensor memory.*durable, decaying "thoughts" recalled by concept/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Trust memory.*snapshots, provable diffs, artifact lineage/)
    ).toBeInTheDocument();

    expect(screen.getByTestId("current-selection")).toHaveTextContent("taosmd");
  });

  it("toggling tmrfs adds it to the selection alongside taosmd", () => {
    stubFetch();
    render(<Wrapper />);

    const tmrfs = screen.getByRole("checkbox", { name: /tmrfs/i });
    fireEvent.click(tmrfs);

    expect(tmrfs).toBeChecked();
    expect(screen.getByTestId("current-selection")).toHaveTextContent("taosmd,tmrfs");

    // Unchecking removes it again.
    fireEvent.click(tmrfs);
    expect(screen.getByTestId("current-selection")).toHaveTextContent("taosmd");
    expect(screen.getByTestId("current-selection")).not.toHaveTextContent("tmrfs");
  });

  it("toggling pk-trust adds it independently of tmrfs", () => {
    stubFetch();
    render(<Wrapper />);

    const pkTrust = screen.getByRole("checkbox", { name: /pk-trust/i });
    fireEvent.click(pkTrust);

    expect(pkTrust).toBeChecked();
    expect(screen.getByTestId("current-selection")).toHaveTextContent("taosmd,pk-trust");
    expect(screen.getByRole("checkbox", { name: /tmrfs/i })).not.toBeChecked();
  });
});
