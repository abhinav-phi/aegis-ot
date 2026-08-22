/** All badge components. Plan-status and validator-verdict are visually
 *  distinct families (UX-001); color is never the only signal. */

export function PlanStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    draft_for_validation: "bg-t3/20 text-t2",
    validated: "bg-info/10 text-info",
    approved: "bg-ok/10 text-ok",
    superseded: "bg-t3/20 text-t3",
    executing: "bg-warn/10 text-warn",
    executed: "bg-ok/10 text-ok",
    rejected: "bg-danger/10 text-danger",
    escalated: "bg-danger/10 text-danger",
    draft_only: "bg-t3/20 text-t3",
  };
  const labels: Record<string, string> = { executed: "EXECUTED (SIM)", draft_only: "DRAFT ONLY (NAIVE)" };
  return (
    <span className={`badge ${map[status] ?? "bg-t3/20 text-t2"}`}
          data-testid={`plan-status-${status}`}>
      {(labels[status] ?? status).toUpperCase()}
    </span>
  );
}

export function VerdictBadge({ verdict }: { verdict: string | null }) {
  if (!verdict) return <span className="badge bg-t3/20 text-t2">NO VERDICT</span>;
  const map: Record<string, string> = {
    allow: "bg-ok/10 text-ok", require_approval: "bg-warn/10 text-warn",
    block: "bg-danger/10 text-danger", escalate: "bg-danger/10 text-danger",
  };
  return (
    <span className={`badge ${map[verdict] ?? ""}`} data-testid={`verdict-${verdict}`}>
      {verdict === "allow" ? "ALLOW · AUTO" : verdict.replace("_", " ").toUpperCase()}
    </span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, string> = {
    low: "bg-info/10 text-info", medium: "bg-warn/10 text-warn",
    high: "bg-danger/20 text-[#fb923c]", critical: "bg-danger/20 text-danger",
  };
  return <span className={`badge ${map[severity] ?? ""}`}>{severity.toUpperCase()}</span>;
}

export type BadgeKey = "trusted" | "public" | "hostile";

export function TierChip({ tier, stale }: { tier: string; stale?: boolean }) {
  const map: Record<BadgeKey, string> = {
    trusted: "bg-ok/10 text-ok", public: "bg-warn/10 text-warn",
    hostile: "bg-danger/10 text-danger",
  };
  return (
    <span className={`badge ${map[tier as BadgeKey] ?? "bg-t3/20 text-t2"}`}>
      {tier.toUpperCase()}{stale ? " · STALE" : ""}
    </span>
  );
}

export function SimulatedBadge() {
  return <span className="badge bg-warn/10 text-warn">SIMULATED</span>;
}

export function FixtureBadge() {
  return <span className="badge bg-info/10 text-info">FIXTURE</span>;
}
