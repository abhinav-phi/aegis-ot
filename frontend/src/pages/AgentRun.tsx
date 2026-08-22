import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api";
import { TierChip } from "../components/Badges";

/** Agent reasoning trace (Design §5.9). Payloads render as plain text JSON. */
export default function AgentRun() {
  const { runId } = useParams();
  const [data, setData] = useState<Awaited<ReturnType<typeof api.agentRun>>["data"] | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!runId) return;
    api.agentRun(runId).then((r) => setData(r.data)).catch(() => {});
    const es = new EventSource(`/api/agent/${runId}/stream`);
    es.onopen = () => setConnected(true);
    es.addEventListener("done", () => es.close());
    es.onerror = () => { setConnected(false); es.close(); };
    return () => es.close();
  }, [runId]);

  if (!data) return <div className="text-t3 text-sm">Loading…</div>;
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-xl font-bold">Agent Run</h1>
        <span className="badge bg-t3/20 text-t2">{data.variant.toUpperCase()}</span>
        <span className="badge bg-info/10 text-info">{data.status.toUpperCase()}</span>
        <span className="text-xs text-t2">step {data.steps}/12</span>
        <span className={`text-xs ${connected ? "text-ok" : "text-warn"}`}>
          {connected ? "SSE live" : "SSE offline — polling fallback"}
        </span>
      </div>
      <div className="panel divide-y divide-cyan1/10">
        {data.messages.map((m, i) => (
          <div key={i} className="px-4 py-2 text-sm">
            <div className="font-mono text-xs text-cyan1 uppercase">{m.role}{m.tool_name ? ` · ${m.tool_name}` : ""}</div>
            <pre className="text-xs text-t2 whitespace-pre-wrap overflow-x-auto">
              {JSON.stringify(m.payload, null, 1).slice(0, 800)}
            </pre>
          </div>
        ))}
      </div>
      <TierChip tier="trusted" />
    </div>
  );
}
