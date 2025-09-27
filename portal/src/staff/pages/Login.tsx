import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useStaffAuth } from "../state/StaffAuthContext";

export default function StaffLogin() {
  const { login } = useStaffAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-8">
      <form
        className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md grid gap-3"
        onSubmit={async (event) => {
          event.preventDefault();
          setErr(null);
          try {
            await login(email, password);
            navigate("/staff");
          } catch (error: any) {
            setErr(error?.response?.data?.detail || error?.message || "Login failed");
          }
        }}
      >
        <h1 className="text-2xl font-semibold text-slate-900">Staff Login</h1>
        <input
          className="border rounded px-3 py-2"
          placeholder="Email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <input
          type="password"
          className="border rounded px-3 py-2"
          placeholder="Password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <button className="bg-orange-500 text-white rounded px-4 py-2">Sign in</button>
        {err && <p className="text-sm text-red-600">{err}</p>}
      </form>
    </div>
  );
}
