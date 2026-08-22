import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { PlanStatusBadge, SimulatedBadge, VerdictBadge } from "../components/Badges";

type Approval = {
  id: string; plan_id: string; revision: number | null;
  hash_suffix: string | null; expires_at: string; requested_by: string;
};

/** Approval queue + modal (Design §5.11, §38 contract): revision identity,
 *  hash suffix, expiry countdown, distinct status vs verdict badges,
 *  invariant-review checkbox on critical, plain-text everything. */
export default function Approvals() {
  const nav = useNavigate();
  const [rows, setRows] = useState<Approval[]>([]);
  const [selected, setSelected] = useState<Approval | null>(null);
  const [checks, setChecks] = useState<Array<{ check: string; status: string; detail: string }>>([]);
  const [verdict, setVerdict] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [invariantsReviewed, setInvariantsReviewed] = useState(false);
  const [error, setError] = useState("");
  const [now, setNow] = useState(Date.now());

  const refresh = () => api.approvals().then((r) => setRows(r.data)).catch(() => setRows([]));
  useEffect(() => {
    refresh();
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);

  async function open(a: Approval) {
    setSelected(a);
    setReason(""); setError(""); setInvariantsReviewed(false);
    const v = await api.validator(a.plan_id).catch(() => null);
    if (v) { setChecks(v.data.checks as typeof checks); setVerdict(v.data.verdict); }
  }

  async function act(fn: () => Promise<unknown>) {
    try { await fn(); setSelected(null); refresh(); }
    catch (e) { setError(String(e).replace("Error: ", "")); refresh(); }
  }

  const expiresInMin = selected
    ? Math.max(0, Math.round((new Date(selected.expires_at).getTime() - now) / 60000))
    : 0;
  const expiringSoon = expiresInMin < 5;

  return (
    <div className="space-y-4">
      <h1 className="font-display text-xl font-bold">Pending Approvals</h1>
      <div className="panel divide-y divide-cyan1/10">
        {rows.length === 0 && <div className="px-4 py-10 text-center text-t3 text-sm">Queue empty.</div>}
        {rows.map((a) => (
          <button key={a.id} onClick={() => open(a)}
                  className="w-full text-left px-4 py-3 hover:bg-elevated/60 flex items-center gap-3">
            <span className="font-mono text-xs">{a.id.slice(0, 8)}</span>
            <span className="text-xs text-t2">rev {a.revision}</span>
            {a.hash_suffix && <span className="font-mono text-xs text-cyan1">#{a.hash_suffix}</span>}
            <span className="ml-auto font-mono text-xs text-t2">
              expires in {Math.max(0, Math.round((new Date(a.expires_at).getTime() - now) / 60000))}m
            </span>
          </button>
        ))}
      </div>

      {selected && (
        <div className="fixed inset-0 bg-abyss/80 grid place-items-center" role="dialog" aria-modal>
          <div className="panel w-[560px] p-5 space-y-3">
            <div className="flex items-center gap-2">
              <h2 className="font-display font-bold">Approve revision {selected.revision}</h2>
              <span className="font-mono text-xs text-cyan1">#{selected.hash_suffix}</span>
            </div>
            <div className="flex items-center gap-2">
              <PlanStatusBadge status="validated" />
              <VerdictBadge verdict={verdict} />
              <SimulatedBadge />
            </div>
            <p className="text-xs text-t2">Action executes ONLY inside the simulator.</p>
            <div className={`text-xs font-mono ${expiringSoon ? "text-danger" : "text-t2"}`}>
              expires in {expiresInMin} min{expiringSoon ? " — approval will fail closed" : ""}
            </div>
            <ul className="text-xs font-mono space-y-1 max-h-40 overflow-y-auto">
              {checks.map((c, i) => (
                <li key={i} className={c.status === "pass" ? "text-ok" : c.status === "fail" ? "text-danger" : "text-warn"}>
                  {c.check} · {c.status} · {c.detail}
                </li>
              ))}
            </ul>
            {error && <div role="alert" className="text-danger text-xs">{error}</div>}
            <textarea className="w-full bg-elevated rounded p-2 text-xs" rows={2}
                      placeholder="Deny reason (required for deny)"
                      value={reason} onChange={(e) => setReason(e.target.value)} />
            <label className="flex items-center gap-2 text-xs text-t2">
              <input type="checkbox" checked={invariantsReviewed}
                     onChange={(e) => setInvariantsReviewed(e.target.checked)} />
              I reviewed the invariant outcomes for this revision
            </label>
            <div className="flex gap-2 justify-end">
              <button className="px-3 py-1.5 rounded border border-cyan1/30 text-xs"
                      onClick={() => act(() => api.amend(selected.id, []))}>
                Amend (creates new revision)
              </button>
              <button className="px-3 py-1.5 rounded bg-danger/10 border border-danger/30 text-danger text-xs"
                      disabled={!reason.trim()}
                      onClick={() => act(() => api.deny(selected.id, reason))}>
                Deny
              </button>
              <button className="px-3 py-1.5 rounded bg-cyan1 text-abyss text-xs font-semibold disabled:opacity-40"
                      disabled={!invariantsReviewed}
                      onClick={() => act(async () => {
                        await api.approve(selected.id);
                        nav(`/incidents`); })}
                      title="Approve & Simulate">
                Approve &amp; Simulate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
