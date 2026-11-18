import { Check, ChevronLeft, LockKeyhole } from "lucide-react";
import { useContext, useEffect, useState, type FormEvent } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { api, type Alert } from "../api";

import {
  Auth,
  Badge,
  ErrorMessage,
  EventTable,
  Loading,
  Panel,
  date,
  label,
  useData,
} from "../shared";
export default function AlertDetail() {
  const id = useLocation().pathname.split("/").pop();
  const { user } = useContext(Auth);
  const { data, error, loading, refresh } = useData<Alert>("/alerts/" + id);
  const [status, setStatus] = useState("");
  const [note, setNote] = useState("");
  const [saveError, setSaveError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (data) setStatus(data.status);
  }, [data]);
  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setSaveError("");
    try {
      await api("/alerts/" + id, {
        method: "PATCH",
        body: JSON.stringify({
          status,
          note,
          expected_updated_at: data?.updated_at,
        }),
      });
      setNote("");
      refresh();
    } catch (e: any) {
      setSaveError(e.message);
    } finally {
      setBusy(false);
    }
  }
  if (loading) return <Loading />;
  if (error || !data) return <ErrorMessage error={error} />;
  return (
    <>
      <NavLink className="back-link" to="/alerts">
        <ChevronLeft size={16} /> Back to alerts
      </NavLink>
      <div className="detail-heading">
        <div>
          <span className="eyebrow">
            {data.rule_id} / ALERT #{data.id} {data.is_demo ? "· DEMO" : ""}
          </span>
          <h2>{data.description.split(":")[0]}</h2>
          <p>{data.description}</p>
        </div>
        <Badge value={data.severity} />
        <Badge value={data.status} />
      </div>
      <div className="detail-grid">
        <div>
          <Panel
            title="Related evidence"
            sub={`${data.events?.length || 0} correlated events · Maximum 200 per alert`}
          >
            <EventTable items={data.events || []} />
          </Panel>
          <Panel
            title="Investigation history"
            sub="Status changes and analyst notes"
          >
            <div className="history">
              {data.history?.map((h) => (
                <div key={h.id}>
                  <span className="history-dot" />
                  <div>
                    <strong>{label(h.new_status)}</strong>
                    <small>
                      {date(h.created_at)} ·{" "}
                      {h.actor_id ? `User #${h.actor_id}` : "Detection engine"}
                    </small>
                    <p>{h.note}</p>
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        </div>
        <Panel
          title="Update investigation"
          sub={
            user?.role === "admin"
              ? "Record your reasoning and next steps"
              : "Administrator access required to edit"
          }
        >
          {user?.role === "admin" ? (
            <form className="form-pad" onSubmit={save}>
              <label>
                Status
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                >
                  {["open", "investigating", "resolved"].map((x) => (
                    <option key={x} value={x}>
                      {label(x)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Investigation note
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  required
                  maxLength={2000}
                  rows={7}
                  placeholder="What did you find? Include evidence and the reason for this status."
                />
              </label>
              <small className="muted">
                Do not include passwords, tokens or other secrets.
              </small>
              <ErrorMessage error={saveError} />
              <button
                disabled={busy || !note.trim()}
                className="button primary full"
              >
                {busy ? "Saving…" : "Save investigation"}
                <Check size={16} />
              </button>
            </form>
          ) : (
            <div className="form-pad">
              <LockKeyhole />
              <p>
                You can review all evidence. Ask an administrator to update this
                investigation.
              </p>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}
