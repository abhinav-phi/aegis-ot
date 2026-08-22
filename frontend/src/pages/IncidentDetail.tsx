import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { SeverityBadge, TierChip } from "../components/Badges";

/** Incident detail: attribution bars + explanation card + MITRE mapping.
 *  All model/telemetry text rendered as PLAIN TEXT (SEC-010). */
export default function IncidentDetail() {
  const { id } = useParams();
  const [data, setData] = useState<Awaited<ReturnType<typeof api.incident>>["data"] | null>(null);

  useEffect(() => { if (id) api.incident(id).then((r) => setData(r.data)).catch(() => {}); }, [id]);
  if (!data) return <div className="text-t3 text-sm">Loading…</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-xl font-bold">{data.title}</h1>
        <SeverityBadge severity={data.severity} />
        <span className="badge bg-t3/20 text-t2">{data.status.toUpperCase()}</span>
        <span className="badge bg-info/10 text-info">DIAGNOSIS = HYPOTHESIS</span>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <section className="col-span-5 panel p-4 space-y-3">
          <h2 className="font-display text-sm font-semibold text-cyan1">Attribution</h2>
          {data.anomalies.map((a) => (
            <div key={a.anomaly_id} className="space-y-1">
              {(a.top_sensors ?? []).map((s) => (
                <div key={s.sensor} className="flex items-center gap-2">
                  <span className="font-mono text-xs w-20">{s.sensor}</span>
                  <div className="flex-1 h-2 bg-elevated rounded overflow-hidden">
                    <div className="h-full bg-warn" style={{ width: `${s.contribution_pct}%` }} />
                  </div>
                  <span className="font-mono text-xs text-t2 w-12 text-right">
                    {s.contribution_pct}%
                  </span>
                </div>
              ))}
              {a.low_confidence && (
                <span className="badge bg-warn/10 text-warn">LOW CONFIDENCE ATTRIBUTION</span>
              )}
            </div>
          ))}
        </section>

        <section className="col-span-7 panel p-4 space-y-3">
          <h2 className="font-display text-sm font-semibold text-cyan1">Explanation (hypothesis)</h2>
          {data.anomalies.map((a) => (
            <p key={a.anomaly_id} className="text-sm whitespace-pre-wrap">{a.hypothesis}</p>
          ))}
          <h3 className="text-xs uppercase tracking-wide text-t2 mt-2">Invariants</h3>
          <ul className="text-xs font-mono space-y-1">
            {(data.anomalies[0]?.invariant_checks ?? []).map((c) => (
              <li key={c.rule_id} className={c.pass ? "text-ok" : "text-danger"}>
                {c.pass ? "PASS" : "FAIL"} · {c.rule_id}
              </li>
            ))}
          </ul>
          <h3 className="text-xs uppercase tracking-wide text-t2 mt-2">MITRE ATT&amp;CK for ICS</h3>
          {data.threat_mappings.map((t) => (
            <div key={t.technique_id} className="flex items-center gap-2 text-sm">
              <span className="font-mono text-cyan1">{t.technique_id}</span>
              <span className="text-t2">confidence {(t.confidence * 100).toFixed(0)}%</span>
            </div>
          ))}
          <TierChip tier="trusted" />
        </section>
      </div>
    </div>
  );
}
