import { useEffect, useState } from "react";

export default function AuditPage() {
  const [rows, setRows] = useState<Array<{ action: string; entity: string; actor: string; at: string }>>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/api/audit").then(async (r) => {
      if (!r.ok) { setError("admin role required"); return; }
      setRows((await r.json()).data);
    }).catch(() => setError("load failed"));
  }, []);
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-xl font-bold">Audit Log</h1>
        <a href="/api/audit/export.csv" className="badge bg-info/10 text-info">EXPORT CSV</a>
      </div>
      {error && <div role="alert" className="text-warn text-xs">{error}</div>}
      <div className="panel divide-y divide-cyan1/10 max-h-[70vh] overflow-y-auto">
        {rows.map((r, i) => (
          <div key={i} className="px-4 py-2 text-xs font-mono flex gap-4">
            <span className="text-t3">{r.at.slice(0, 19)}</span>
            <span className="text-cyan1">{r.action}</span>
            <span className="text-t2 truncate">{r.entity}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
