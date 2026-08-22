import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Datasets() {
  const [rows, setRows] = useState<Array<{ id: string; key: string; sha256: string; rows: number; primary: boolean }>>([]);
  const [path, setPath] = useState("");
  const [key, setKey] = useState("synthetic");
  const [error, setError] = useState("");

  const refresh = () => fetch("/api/datasets").then(async (r) => {
    if (r.ok) setRows((await r.json()).data); else setError("admin role required");
  }).catch(() => setError("load failed"));

  useEffect(() => { refresh(); }, []);

  async function ingest() {
    setError("");
    try {
      const res = await fetch(`/api/datasets/ingest/${key}`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_path: path }),
      });
      if (!res.ok) throw new Error((await res.json()).code || "ingest failed");
      refresh();
    } catch (e) { setError(String(e).replace("Error: ", "")); }
  }

  return (
    <div className="space-y-4">
      <h1 className="font-display text-xl font-bold">Dataset Registry</h1>
      <p className="text-xs text-t2">Licensed SWaT/WUSTL ingestion is a manual hash-pinned step (DEC-016).</p>
      <div className="panel divide-y divide-cyan1/10">
        {rows.map((d) => (
          <div key={d.id} className="px-4 py-2 flex items-center gap-3 text-sm">
            <span className="font-mono text-cyan1">{d.key}</span>
            <span className="font-mono text-xs text-t2">sha256:{d.sha256}…</span>
            <span className="ml-auto text-xs text-t2">{d.rows} rows</span>
            {d.primary && <span className="badge bg-ok/10 text-ok">PRIMARY</span>}
          </div>
        ))}
      </div>
      <div className="panel p-4 space-y-2">
        <h2 className="text-sm font-semibold">Ingest from local file path</h2>
        <input className="w-full bg-elevated rounded px-3 py-2 text-xs" placeholder="/path/to/data.csv"
               value={path} onChange={(e) => setPath(e.target.value)} />
        <select className="bg-elevated rounded px-3 py-2 text-xs" value={key}
                onChange={(e) => setKey(e.target.value)}>
          {["swat", "wustl_iiot2021", "wadi", "synthetic"].map((k) => <option key={k}>{k}</option>)}
        </select>
        <button onClick={ingest} className="px-3 py-1.5 rounded bg-cyan1 text-abyss text-xs font-semibold">
          Ingest
        </button>
        {error && <div role="alert" className="text-danger text-xs">{error}</div>}
      </div>
    </div>
  );
}
