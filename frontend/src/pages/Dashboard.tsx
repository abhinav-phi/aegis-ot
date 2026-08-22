import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { SeverityBadge, SimulatedBadge } from "../components/Badges";

export default function Dashboard() {
  const [telemetry, setTelemetry] = useState<Array<{ window_start: string; score: number; is_anomaly: boolean }>>([]);
  const [lastUpdate, setLastUpdate] = useState<string>("");
  const [stale, setStale] = useState(false);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const res = await api.telemetry();
        if (!stop) { setTelemetry(res.data); setStale(false); setLastUpdate(new Date().toISOString().slice(11, 19) + "Z"); }
      } catch { if (!stop) setStale(true); }
    };
    tick();
    const t = setInterval(tick, 1000); // AppFlow §7 polling
    return () => { stop = true; clearInterval(t); };
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold">Live Telemetry</h1>
        <span className="text-xs text-t2 font-mono" title={stale ? "STALE — backend unreachable" : "live"}>
          {stale ? "STALE" : `updated ${lastUpdate}`}
        </span>
      </div>
      <div className="panel divide-y divide-cyan1/10">
        {telemetry.length === 0 && <EmptyState label="No telemetry yet — run the pipeline." />}
        {telemetry.slice(0, 20).map((t) => (
          <div key={t.window_start} className="flex items-center justify-between px-4 py-2 text-sm">
            <span className="font-mono text-xs text-t2">{t.window_start}</span>
            <span className="font-mono">{t.score.toFixed(3)}</span>
            {t.is_anomaly ? <SeverityBadge severity="high" /> : <SimulatedBadge />}
          </div>
        ))}
      </div>
    </div>
  );
}

export function EmptyState({ label }: { label: string }) {
  return <div className="px-4 py-10 text-center text-t3 text-sm">{label}</div>;
}
