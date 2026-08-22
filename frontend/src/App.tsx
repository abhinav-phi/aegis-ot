import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import AgentRun from "./pages/AgentRun";
import Approvals from "./pages/Approvals";
import AuditPage from "./pages/AuditPage";
import Dashboard from "./pages/Dashboard";
import Datasets from "./pages/Datasets";
import DemoPage from "./pages/DemoPage";
import EvalPage from "./pages/EvalPage";
import IncidentDetail from "./pages/IncidentDetail";
import Incidents from "./pages/Incidents";
import Login from "./pages/Login";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/incidents" element={<Incidents />} />
        <Route path="/incidents/:id" element={<IncidentDetail />} />
        <Route path="/agent/:runId" element={<AgentRun />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="/demo/attack" element={<DemoPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/eval" element={<EvalPage />} />
        <Route path="/datasets" element={<Datasets />} />
      </Route>
    </Routes>
  );
}
