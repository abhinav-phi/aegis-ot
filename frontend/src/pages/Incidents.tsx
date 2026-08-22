import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { SeverityBadge } from "../components/Badges";

export default function Incidents() {
  const [rows, setRows] = useState<Array<{ id: string; severity: string; status: string; title: string; start_ts: string }>>([]);
  useEffect(() => { api.incidents().then((r) => setRows(r.data)).catch(() => setRows([])); }, []);
  return (
    <div className="space-y-4">
      <h1 className="font-display text-xl font-bold">Incidents</h1>
      <div className="panel divide-y divide-cyan1/10">
        {rows.length === 0 && (
          <div className="px-4 py-10 text-center text-t3 text-sm">No incidents yet.</div>
        )}
        {rows.map((i) => (
          <Link key={i.id} to={`/incidents/${i.id}`}
                className="flex items-center justify-between px-4 py-3 hover:bg-elevated/60">
            <span className="font-mono text-xs">{i.id.slice(0, 8)}</span>
            <span className="text-sm flex-1 mx-4 truncate">{i.title}</span>
            <SeverityBadge severity={i.severity} />
            <span className="badge bg-t3/20 text-t2 ml-2">{i.status.toUpperCase()}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
