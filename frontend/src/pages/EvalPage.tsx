import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function EvalPage() {
  const [rows, setRows] = useState<Array<{ metric: string; value: number; source: string }>>([]);
  useEffect(() => { api.evalMetrics().then((r) => setRows(r.data)).catch(() => {}); }, []);
  return (
    <div className="space-y-4">
      <h1 className="font-display text-xl font-bold">Evaluation Metrics</h1>
      <p className="text-xs text-t2">All values are measured outputs — targets are labeled TARGET elsewhere.</p>
      <div className="panel overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead><tr className="bg-elevated text-left text-t2 uppercase tracking-wider">
            <th className="px-3 py-2">source</th><th className="px-3 py-2">metric</th>
            <th className="px-3 py-2">value</th>
          </tr></thead>
          <tbody className="divide-y divide-cyan1/10">
            {rows.map((r, i) => (
              <tr key={i}><td className="px-3 py-2">{r.source}</td>
                <td className="px-3 py-2">{r.metric}</td>
                <td className="px-3 py-2">{r.value.toFixed(4)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
