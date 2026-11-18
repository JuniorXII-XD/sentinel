import {
  ArrowRight,
  Eye,
  Fingerprint,
  LockKeyhole,
  Shield,
} from "lucide-react";
import { useContext, useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, setCsrf } from "../api";

import { Auth, ErrorMessage } from "../shared";
export default function Login() {
  const auth = useContext(Auth);
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [show, setShow] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const f = new FormData(e.currentTarget);
    try {
      const result = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(f)),
      });
      setCsrf(result.csrf_token);
      const me = await api("/auth/me");
      auth.setDemo(me.demo_enabled);
      auth.setUser(result.user);
      navigate("/overview");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  if (auth.user) return <Navigate to="/overview" />;
  return (
    <div className="login-page">
      <div className="login-story">
        <div className="brand">
          <Shield />
          <span>
            SENTINEL<span className="brand-mark">.</span>
          </span>
        </div>
        <div className="login-art">
          <div className="radar-ring r1" />
          <div className="radar-ring r2" />
          <div className="radar-ring r3" />
          <div className="radar-core">
            <Fingerprint size={68} />
          </div>
          <span className="radar-point p1" />
          <span className="radar-point p2" />
          <span className="radar-label">VISIBILITY. CONTEXT. CONFIDENCE.</span>
        </div>
        <div className="login-copy">
          <span className="eyebrow">SECURITY EVENT INTELLIGENCE</span>
          <h1>
            Every event tells
            <br />a <em>security story.</em>
          </h1>
          <p>
            Understand the signals. Investigate with context.
            <br />
            Bring clarity to your security operations.
          </p>
        </div>
        <footer>
          Built for learning. Designed for investigation.
          <span>STANDARD / 1.0</span>
        </footer>
      </div>
      <div className="login-form-wrap">
        <div className="login-form">
          <span className="form-lock">
            <LockKeyhole size={23} />
          </span>
          <span className="eyebrow">YOUR OPERATIONS WORKSPACE</span>
          <h2>Welcome back</h2>
          <p>Sign in to your SENTINEL account.</p>
          <form onSubmit={submit}>
            <label>
              Username
              <input
                name="username"
                autoComplete="username"
                placeholder="Your username"
                maxLength={80}
                required
              />
            </label>
            <label>
              Password
              <div className="password-wrap">
                <input
                  name="password"
                  type={show ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  maxLength={128}
                  required
                />
                <button
                  type="button"
                  className="icon-btn"
                  aria-label={show ? "Hide password" : "Show password"}
                  onClick={() => setShow(!show)}
                >
                  <Eye size={18} />
                </button>
              </div>
            </label>
            <ErrorMessage error={error} />
            <button disabled={busy} className="button primary full">
              {busy ? "Signing in…" : "Sign in to workspace"}
              <ArrowRight size={17} />
            </button>
          </form>
          <div className="login-notice">
            <Shield size={16} />
            <span>
              Protected session · Role-based access
              <br />
              Need access? Contact your administrator.
            </span>
          </div>
        </div>
        <div className="login-bottom">
          <span className="dot green" /> Secure by design{" "}
          <span>© SENTINEL / NIOR</span>
        </div>
      </div>
    </div>
  );
}
