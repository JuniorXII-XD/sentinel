import {
  Check,
  CircleHelp,
  Clock3,
  FlaskConical,
  LockKeyhole,
  Server,
  Shield,
  UserPlus,
} from "lucide-react";
import { useContext, useEffect, useState, type FormEvent } from "react";
import { api, type User } from "../api";

import { Auth, Badge, ErrorMessage, Loading, Panel, useData } from "../shared";
export default function SettingsPage() {
  const { user } = useContext(Auth);
  const { data, error, loading, refresh } = useData<any>("/settings");
  const [users, setUsers] = useState<User[]>([]);
  const [message, setMessage] = useState("");
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (user?.role === "admin")
      api<User[]>("/settings/users")
        .then(setUsers)
        .catch((e) => setActionError(e.message));
  }, [user]);
  async function run(fn: () => Promise<any>, text: string) {
    setBusy(true);
    setActionError("");
    setMessage("");
    try {
      await fn();
      setMessage(text);
      refresh();
      if (user?.role === "admin") setUsers(await api("/settings/users"));
    } catch (e: any) {
      setActionError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function add(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const body = JSON.stringify(Object.fromEntries(new FormData(form)));
    await run(async () => {
      await api("/settings/users", { method: "POST", body });
      form.reset();
    }, "Account created. Share its credentials privately.");
  }
  if (loading) return <Loading />;
  if (error || !data) return <ErrorMessage error={error} />;
  return (
    <>
      <ErrorMessage error={actionError} />
      {message && (
        <div role="status" className="success-message">
          <Check size={16} />
          {message}
        </div>
      )}
      <div className="settings-summary">
        <div>
          <Server />
          <span>
            Environment<strong>{data.environment}</strong>
          </span>
        </div>
        <div>
          <Clock3 />
          <span>
            Work hours
            <strong>
              {data.work_start}:00–{data.work_end}:00 · {data.timezone}
            </strong>
          </span>
        </div>
        <div>
          <LockKeyhole />
          <span>
            Session policy
            <strong>
              {data.session_hours}h absolute / {data.idle_minutes}m idle
            </strong>
          </span>
        </div>
      </div>
      <Panel
        title="Detection coverage"
        sub="Admins can enable or disable rules. Numeric parameters are read-only here and managed in the database."
      >
        <div className="rule-list">
          {data.rules.map((r: any) => (
            <div key={r.id}>
              <span className={`rule-icon ${r.enabled ? "enabled" : ""}`}>
                <Shield size={20} />
              </span>
              <div>
                <span className="mono">{r.id}</span>
                <h3>{r.name}</h3>
                <p>{r.description}</p>
                <small>
                  {r.window_seconds}s{" "}
                  {r.id === "ACCESS-001" || r.id === "AUTH-004"
                    ? "deduplication window"
                    : "detection / deduplication window"}
                  {r.id === "AUTH-002" &&
                    ` · minimum ${r.threshold} distinct accounts · maximum ${r.max_attempts_per_account} failures per account`}
                  {(r.id === "AUTH-001" || r.id === "AUTH-003") &&
                    ` · minimum ${r.threshold} failures`}
                  {r.id === "AUTH-003" &&
                    ` · minimum ${r.min_accounts} accounts · minimum ${r.min_source_ips} source IPs`}
                  {(r.id === "ACCESS-001" || r.id === "AUTH-004") &&
                    " · single qualifying event (threshold field unused)"}
                </small>
              </div>
              <Badge value={r.severity} />
              <button
                disabled={busy || user?.role !== "admin"}
                className={`toggle ${r.enabled ? "on" : ""}`}
                role="switch"
                aria-checked={r.enabled}
                aria-label={`Enable ${r.name}`}
                onClick={() =>
                  run(
                    () =>
                      api("/settings/rules/" + r.id, {
                        method: "PATCH",
                        body: JSON.stringify({ enabled: !r.enabled }),
                      }),
                    "Rule updated and audited",
                  )
                }
              >
                <span />
              </button>
            </div>
          ))}
        </div>
      </Panel>
      {user?.role === "admin" && (
        <>
          <Panel
            title="Workspace accounts"
            sub="Role or activation changes revoke all sessions for that account"
          >
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Account</th>
                    <th>Role</th>
                    <th>State</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <strong>{u.username}</strong>
                        {u.id === user.id && <small>Current account</small>}
                      </td>
                      <td>
                        <select
                          aria-label={`Role for ${u.username}`}
                          value={u.role}
                          disabled={busy || u.id === user.id}
                          onChange={(e) =>
                            run(
                              () =>
                                api("/settings/users/" + u.id, {
                                  method: "PATCH",
                                  body: JSON.stringify({
                                    role: e.target.value,
                                    is_active: u.is_active,
                                  }),
                                }),
                              "Access updated; existing sessions revoked",
                            )
                          }
                        >
                          <option value="analyst">Analyst</option>
                          <option value="admin">Admin</option>
                        </select>
                      </td>
                      <td>
                        <Badge value={u.is_active ? "active" : "disabled"} />
                      </td>
                      <td>
                        <button
                          className="button secondary compact"
                          disabled={busy || u.id === user.id}
                          onClick={() =>
                            run(
                              () =>
                                api("/settings/users/" + u.id, {
                                  method: "PATCH",
                                  body: JSON.stringify({
                                    role: u.role,
                                    is_active: !u.is_active,
                                  }),
                                }),
                              "Account state updated",
                            )
                          }
                        >
                          {u.is_active ? "Disable" : "Enable"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
          <Panel
            title="Add an account"
            sub="Use a unique password of at least 12 characters"
          >
            <form className="new-user-form" onSubmit={add}>
              <label>
                Username
                <input
                  name="username"
                  pattern="[a-zA-Z0-9_.\-]+"
                  maxLength={80}
                  required
                  autoComplete="off"
                />
              </label>
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  minLength={12}
                  maxLength={128}
                  autoComplete="new-password"
                  required
                />
              </label>
              <label>
                Role
                <select name="role">
                  <option value="analyst">Analyst</option>
                  <option value="admin">Admin</option>
                </select>
              </label>
              <button disabled={busy} className="button primary">
                <UserPlus size={17} />
                Create account
              </button>
            </form>
          </Panel>
          {data.demo_enabled && (
            <Panel
              title="Development lab"
              sub="Authenticated synthetic data · Documentation IP ranges only"
            >
              <div className="demo-settings">
                <FlaskConical size={28} />
                <p>
                  Create repeatable examples for all five detection rules. The
                  dataset is isolated from live activity; repeated seeding does
                  not duplicate it.
                </p>
                <button
                  disabled={busy}
                  className="button secondary"
                  onClick={() =>
                    run(
                      () => api("/demo/seed", { method: "POST" }),
                      "Demo dataset is ready. Select “Demo dataset” in the top toolbar.",
                    )
                  }
                >
                  Generate demo events
                </button>
              </div>
            </Panel>
          )}
        </>
      )}
      <div className="info-box">
        <CircleHelp size={18} />
        <p>
          This system observes its own authentication and authorization events.
          External log collectors, MFA, tamper-proof archival and automated
          blocking are outside this release. Working hours and security policy
          are configured on the server.
        </p>
      </div>
    </>
  );
}
