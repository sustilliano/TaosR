import { useState, useEffect, useCallback } from "react";
import { Check, Copy, ExternalLink, Fingerprint, Loader2, Minus, ReceiptText, ShieldCheck, X } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  AgentProvenancePanel — Bean-0 provenance record for one agent      */
/*  (docs/design/silicon-bean-integration.md)                          */
/* ------------------------------------------------------------------ */

interface ProvenanceRecord {
  substrate?: string;
  framework?: string;
  framework_ref?: string;
  installer_sha256?: string;
  constitution_sha256?: string;
  model_id?: string;
  model_file_sha256?: string;
  corpus_refs?: string[];
  recorded_at?: string | number;
}

interface InferenceReceipt {
  inference_id?: string;
  completed_at?: string | number;
}

interface ReceiptsSummary {
  count: number;
  newestCompletedAt: string | number | null;
  latestInferenceId: string | null;
}

type LinkStatus = "pass" | "fail" | "unknown";

interface AttestationLink {
  name: string;
  status: LinkStatus;
  detail?: string;
}

interface Attestation {
  overall: string; // "verified" | "partial" | "broken"
  links: AttestationLink[];
}

/** Parse a recorded_at / completed_at value (ISO string or unix seconds). */
function toDate(value: string | number | null | undefined): Date | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "number") {
    // Heuristic: values below 1e12 are unix seconds, above are milliseconds.
    const d = new Date(value < 1e12 ? value * 1000 : value);
    return isNaN(d.getTime()) ? null : d;
  }
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d;
}

/** Humanize a timestamp: relative when recent, absolute otherwise. */
function fmtWhen(value: string | number | null | undefined): string {
  const d = toDate(value);
  if (!d) return "unknown";
  const delta = Date.now() - d.getTime();
  if (delta >= 0 && delta < 60_000) return "just now";
  if (delta >= 0 && delta < 3_600_000) return `${Math.floor(delta / 60_000)}m ago`;
  if (delta >= 0 && delta < 86_400_000) return `${Math.floor(delta / 3_600_000)}h ago`;
  return d.toLocaleString();
}

/** Shortened monospace hash with full value in tooltip and click-to-copy. */
function HashChip({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    navigator.clipboard?.writeText(value).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      type="button"
      onClick={copy}
      title={value}
      aria-label={`Copy ${label} ${value}`}
      className="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10 font-mono text-xs text-shell-text-secondary transition-colors"
    >
      {value.slice(0, 12)}…
      {copied ? (
        <Check size={10} className="text-green-400 shrink-0" aria-hidden />
      ) : (
        <Copy size={10} className="text-shell-text-tertiary shrink-0" aria-hidden />
      )}
    </button>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="text-[10px] text-shell-text-tertiary uppercase tracking-wider w-28 shrink-0">
        {label}
      </span>
      <span className="text-xs text-shell-text min-w-0">{children}</span>
    </div>
  );
}

const OVERALL_STYLE: Record<string, string> = {
  verified: "bg-emerald-500/20 text-emerald-400",
  partial: "bg-amber-500/20 text-amber-400",
  broken: "bg-red-500/20 text-red-400",
};

function LinkIcon({ status }: { status: LinkStatus }) {
  if (status === "pass")
    return <Check size={11} className="text-emerald-400 shrink-0" aria-label="pass" />;
  if (status === "fail")
    return <X size={11} className="text-red-400 shrink-0" aria-label="fail" />;
  return <Minus size={11} className="text-shell-text-tertiary shrink-0" aria-label="unknown" />;
}

/** The Bean-5 attestation chain: one row per link + an overall verdict. */
function AttestationChain({ attestation }: { attestation: Attestation }) {
  const overall = attestation.overall.toLowerCase();
  return (
    <div className="flex flex-col gap-2 p-3 rounded-xl border border-white/5 bg-white/[0.02]">
      <div className="flex items-center gap-2">
        <ShieldCheck size={13} className="text-shell-text-secondary" aria-hidden />
        <span className="text-[10px] text-shell-text-tertiary uppercase tracking-wider">
          Attestation
        </span>
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
            OVERALL_STYLE[overall] ?? "bg-white/10 text-shell-text-secondary"
          }`}
        >
          {overall}
        </span>
      </div>
      {attestation.links.map((link) => (
        <div key={link.name} className="flex items-baseline gap-2">
          <LinkIcon status={link.status} />
          <span className="text-xs text-shell-text font-mono w-32 shrink-0">{link.name}</span>
          {link.detail && (
            <span className="text-[11px] text-shell-text-tertiary min-w-0 break-words">
              {link.detail}
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

export function AgentProvenancePanel({ agentName }: { agentName: string }) {
  const [loading, setLoading] = useState(true);
  const [record, setRecord] = useState<ProvenanceRecord | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [receipts, setReceipts] = useState<ReceiptsSummary | null>(null);
  const [attestation, setAttestation] = useState<Attestation | null>(null);
  const [attesting, setAttesting] = useState(false);
  const [attestError, setAttestError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/agents/${encodeURIComponent(agentName)}/provenance`,
      );
      if (res.status === 404) {
        setNotFound(true);
        setRecord(null);
      } else if (res.ok) {
        const data = await res.json();
        // The endpoint may return the record bare or wrapped in an
        // {agent_name, record, ...} envelope; accept both.
        const rec: ProvenanceRecord = (data?.record ?? data) as ProvenanceRecord;
        setRecord(rec);
        setNotFound(false);
      } else {
        // Non-404 failure: degrade to the quiet empty state, never a toast.
        setNotFound(true);
        setRecord(null);
      }
    } catch {
      setNotFound(true);
      setRecord(null);
    }
    setLoading(false);
  }, [agentName]);

  // Inference receipts (Bean-1) are optional — the endpoint may not exist
  // yet. Any failure means the summary line is simply omitted.
  const loadReceipts = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/agents/${encodeURIComponent(agentName)}/inference-receipts?limit=25`,
      );
      if (!res.ok) {
        setReceipts(null);
        return;
      }
      const data = await res.json();
      const list = (data?.receipts ?? []) as InferenceReceipt[];
      const newest = list.reduce<Date | null>((best, r) => {
        const d = toDate(r.completed_at);
        return d && (!best || d > best) ? d : best;
      }, null);
      // GET returns newest-first, so list[0] is the latest receipt.
      setReceipts({
        count: typeof data?.count === "number" ? data.count : list.length,
        newestCompletedAt: newest ? newest.toISOString() : null,
        latestInferenceId: list[0]?.inference_id ?? null,
      });
    } catch {
      setReceipts(null);
    }
  }, [agentName]);

  // Bean-5 attestation walk — on demand, verify the latest receipt's chain.
  // The endpoint may not exist yet; failures surface as a quiet inline note.
  const verifyLatest = useCallback(async () => {
    const id = receipts?.latestInferenceId;
    if (!id) return;
    setAttesting(true);
    setAttestError(null);
    try {
      const res = await fetch(
        `/api/agents/${encodeURIComponent(agentName)}/attestation/${encodeURIComponent(id)}`,
      );
      if (!res.ok) {
        setAttestError("Attestation unavailable");
        setAttestation(null);
        return;
      }
      const data = await res.json();
      setAttestation({
        overall: String(data?.overall ?? data?.status ?? "unknown"),
        links: (data?.links ?? data?.chain ?? []) as AttestationLink[],
      });
    } catch {
      setAttestError("Attestation unavailable");
      setAttestation(null);
    } finally {
      setAttesting(false);
    }
  }, [agentName, receipts?.latestInferenceId]);

  useEffect(() => {
    setLoading(true);
    setAttestation(null);
    setAttestError(null);
    load();
    loadReceipts();
  }, [load, loadReceipts]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={20} className="animate-spin text-shell-text-tertiary" />
      </div>
    );
  }

  if (notFound || !record) {
    return (
      <div className="p-4">
        <p className="text-sm text-shell-text-tertiary">
          No provenance recorded — Bean-0 not yet run for this agent
        </p>
      </div>
    );
  }

  const corpusRefs = record.corpus_refs ?? [];

  return (
    <div className="h-full overflow-auto p-4">
      <div className="flex flex-col gap-4 max-w-2xl">
        <div className="flex items-center gap-2">
          <Fingerprint size={14} className="text-shell-text-secondary" aria-hidden />
          <p className="text-xs font-medium text-shell-text-tertiary uppercase tracking-wider">
            Provenance
          </p>
          {record.substrate && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-medium">
              {record.substrate}
            </span>
          )}
        </div>

        <div className="flex flex-col gap-2 p-3 rounded-xl border border-white/5 bg-white/[0.02]">
          {record.framework && (
            <Row label="Framework">
              <span className="font-mono">
                {record.framework}
                {record.framework_ref ? `@${record.framework_ref}` : ""}
              </span>
            </Row>
          )}
          {record.model_id && (
            <Row label="Model">
              <span className="font-mono">{record.model_id}</span>
            </Row>
          )}
          {record.constitution_sha256 && (
            <Row label="Constitution">
              <HashChip value={record.constitution_sha256} label="constitution hash" />
            </Row>
          )}
          {record.installer_sha256 && (
            <Row label="Installer">
              <HashChip value={record.installer_sha256} label="installer hash" />
            </Row>
          )}
          {record.model_file_sha256 && (
            <Row label="Model file">
              <HashChip value={record.model_file_sha256} label="model file hash" />
            </Row>
          )}
          {corpusRefs.length > 0 && (
            <Row label="Corpus">
              <span className="flex flex-wrap gap-x-3 gap-y-1">
                {corpusRefs.map((ref) => (
                  /^https?:\/\//.test(ref) ? (
                    <a
                      key={ref}
                      href={ref}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-blue-400 hover:underline break-all"
                    >
                      {ref}
                      <ExternalLink size={10} className="shrink-0" aria-hidden />
                    </a>
                  ) : (
                    <span key={ref} className="font-mono text-shell-text-secondary break-all">
                      {ref}
                    </span>
                  )
                ))}
              </span>
            </Row>
          )}
          <Row label="Recorded">
            <span title={toDate(record.recorded_at)?.toISOString() ?? undefined}>
              {fmtWhen(record.recorded_at)}
            </span>
          </Row>
        </div>

        {receipts && receipts.count > 0 && (
          <div className="flex flex-col gap-2">
            <p className="flex items-center gap-1.5 text-xs text-shell-text-secondary">
              <ReceiptText size={11} className="text-shell-text-tertiary shrink-0" aria-hidden />
              {receipts.count} inference receipt{receipts.count === 1 ? "" : "s"}
              {receipts.newestCompletedAt && (
                <> · newest {fmtWhen(receipts.newestCompletedAt)}</>
              )}
              {receipts.latestInferenceId && (
                <button
                  type="button"
                  onClick={verifyLatest}
                  disabled={attesting}
                  className="ml-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-white/5 hover:bg-white/10 text-xs text-shell-text-secondary transition-colors disabled:opacity-50"
                >
                  {attesting ? (
                    <Loader2 size={10} className="animate-spin" aria-hidden />
                  ) : (
                    <ShieldCheck size={10} aria-hidden />
                  )}
                  Verify latest
                </button>
              )}
            </p>
            {attestError && (
              <p className="text-[11px] text-shell-text-tertiary">{attestError}</p>
            )}
            {attestation && <AttestationChain attestation={attestation} />}
          </div>
        )}
      </div>
    </div>
  );
}
