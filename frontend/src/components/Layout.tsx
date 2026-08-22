import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

/** Command-center frame (Design.md §4.1): top bar + left rail + liveness. */
export default function Layout() {
  const nav = useNavigate();
  const [workerAlive, setWorkerAlive] = useState(false);
  const [stale, setStale] = useState(false);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const res = await fetch("/api/health/worker");
        const body = await res.json();
        if (!stop) {
          setWorkerAlive(Boolean(body.worker_alive));
          setStale(false);
        }
      } catch {
        if (!stop) setStale(true); // UX-003: stale indicator
      }
    };
    tick();
    const t = setInterval(tick, 5000);
    return () => { stop = true; clearInterval(t); };
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-10 bg-panel/90 backdrop-blur border-b border-cyan1/15
                         flex items-center justify-between px-5 h-12">
        <div className="font-display font-bold tracking-wide text-cyan1">AEGIS-OT</div>
        <div className="flex items-center gap-4 text-xs text-t2">
          <span className="badge bg-warn/10 text-warn">DEV</span>
          <span data-testid="liveness"
                title={stale ? "Backend unreachable — showing stale state" : workerAlive ? "Worker OK" : "Worker heartbeat missing"}
                className={`inline-block w-2.5 h-2.5 rounded-full ${stale ? "bg-danger" : workerAlive ? "bg-ok animate-pulse" : "bg-warn"}`} />
          <button className="hover:text-t1" onClick={async () => { await api.logout(); nav("/login"); }}>
            Sign out
          </button>
        </div>
      </header>
      <div className="flex flex-1">
        <nav className="w-[240px] bg-panel border-r border-cyan1/15 p-3 space-y-1 max-md:hidden">
          {[
            ["/dashboard", "Dashboard"],
            ["/incidents", "Incidents"],
            ["/approvals", "Approvals"],
            ["/demo/attack", "Attack Demo"],
            ["/audit", "Audit"],
            ["/eval", "Evaluation"],
            ["/datasets", "Datasets"],
          ].map(([to, label]) => (
            <NavLink key={to} to={to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm ${isActive ? "bg-elevated text-cyan1" : "text-t2 hover:text-t1 hover:bg-elevated/60"}`}>
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1 p-5 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
