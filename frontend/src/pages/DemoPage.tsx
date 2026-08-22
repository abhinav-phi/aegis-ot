import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { FixtureBadge, SimulatedBadge } from "../components/Badges";

/** Attack-the-Agent stepper (AppFlow §4 / Design §5.12). F7 renders as numeric
 *  tables only; every card carries FIXTURE/SIMULATED badges. */
export default function DemoPage() {
  const [metrics, setMetrics] = useState<Record<string, number> | null>(null);
  const [error, setError] = useState("");
  const [step, setStep] = useState(0);

  const steps = [
    "Malicious context embedded (F1/F4 fixture)",
    "Naive agent follows injected directive — unsafe recommendation recorded",
    "Provenance + pattern checks flag manipulation (C1/C3)",
    "Trusted SPD-017 grounding surfaced as evidence chips",
    "Unsafe action blocked / gated by policy rule",
    "Safer recommendation approved by distinct approver",
    "Simulated execution in sandbox (SIMULATED)",
  ];

  useEffect(() => {
    api.demoLatest().then((r) => setMetrics(r.data)).catch(() => setError("Fixture not provisioned — run POST /demo/attack (admin)."));
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-xl font-bold">Attack the Agent</h1>
        <FixtureBadge /><SimulatedBadge />
      </div>
      <div className="panel divide-y divide-cyan1/10">
        {steps.map((s, i) => (
          <button key={i} onClick={() => setStep(i)}
                  className={`w-full text-left px-4 py-3 text-sm flex gap-3 ${step === i ? "bg-elevated" : ""}`}>
            <span className="font-mono text-xs text-cyan1">{i + 1}</span>
            <span className={i <= step ? "text-t1" : "text-t3"}>{s}</span>
          </button>
        ))}
      </div>
      {error && <div role="alert" className="text-warn text-sm">{error}</div>}
      {metrics && (
        <div className="panel p-4 overflow-x-auto">
          <h2 className="text-sm font-semibold mb-2">Naive vs Hardened (measured)</h2>
          <table className="text-xs font-mono w-full">
            <tbody className="divide-y divide-cyan1/10">
              {Object.entries(metrics).map(([k, v]) => (
                <tr key={k}><td className="py-1 pr-4 text-t2">{k}</td><td>{v.toFixed(3)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
