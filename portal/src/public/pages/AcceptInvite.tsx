import { useEffect, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";

import { acceptInvitation } from "../../staff/lib/invitationsFetchers";

export default function AcceptInvite() {
  const { token: paramToken = "" } = useParams();
  const location = useLocation();
  const searchToken = new URLSearchParams(location.search).get("token") || "";
  const token = paramToken || searchToken;

  const formRef = useRef<HTMLFormElement>(null);
  const [message, setMessage] = useState<string>("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setMessage("Missing invitation token.");
    }
  }, [token]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!formRef.current || !token) return;

    const data = new FormData(formRef.current);

    const payload = {
      token,
      password: String(data.get("password") || ""),
      first_name: String(data.get("first_name") || "") || undefined,
      last_name: String(data.get("last_name") || "") || undefined,
      phone: String(data.get("phone") || "") || undefined,
    };

    setMessage("");
    setSuccess(false);

    try {
      await acceptInvitation(payload);
      setSuccess(true);
      setMessage("Success! You can now log in.");
    } catch (error: any) {
      const detail = error?.response?.data?.detail || error?.message || "Failed to accept invitation.";
      setMessage(detail);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <form ref={formRef} className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md grid gap-3" onSubmit={handleSubmit}>
        <h1 className="text-2xl font-semibold text-slate-900">Accept Invitation</h1>

        <input className="border rounded px-3 py-2" name="first_name" placeholder="First name (optional)" />
        <input className="border rounded px-3 py-2" name="last_name" placeholder="Last name (optional)" />
        <input className="border rounded px-3 py-2" name="phone" placeholder="Phone (optional)" />
        <input className="border rounded px-3 py-2" type="password" name="password" placeholder="Password" required />

        <button className="bg-orange-500 text-white rounded px-4 py-2" type="submit">
          Create account
        </button>

        {message && (
          <div className={`${success ? "text-green-700" : "text-red-600"} text-sm`}>{message}</div>
        )}

        {success && (
          <a className="text-blue-700 text-sm" href="/staff/login">
            Go to staff login
          </a>
        )}
      </form>
    </div>
  );
}
