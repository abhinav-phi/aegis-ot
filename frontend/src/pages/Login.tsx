import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";

export default function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const res = await api.login(email, password);
      api.setToken(res.data.access_token);
      nav("/dashboard");
    } catch (err) {
      setError("Invalid credentials"); // anti-enumeration: generic message
    }
  }

  return (
    <div className="min-h-screen grid place-items-center">
      <form onSubmit={submit} className="panel w-96 p-6 space-y-4">
        <h1 className="font-display text-xl font-bold text-cyan1">AEGIS-OT Sign in</h1>
        <p className="text-xs text-t2">Research system — every action is simulated.</p>
        <input className="w-full bg-elevated rounded px-3 py-2 text-sm" type="email"
               placeholder="email" value={email}
               onChange={(e) => setEmail(e.target.value)} required />
        <input className="w-full bg-elevated rounded px-3 py-2 text-sm" type="password"
               placeholder="password" value={password}
               onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        {error && <div role="alert" className="text-danger text-sm">{error}</div>}
        <button className="w-full py-2 rounded bg-cyan1 text-abyss font-semibold hover:bg-glow">
          Sign in
        </button>
      </form>
    </div>
  );
}
