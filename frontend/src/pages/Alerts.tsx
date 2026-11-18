import { ChevronRight, ShieldAlert } from "lucide-react";
import { useContext, useEffect, useState } from "react";
import { NavLink } from "react-router-dom";
import { type Alert } from "../api";

import {
  Badge,
  Empty,
  ErrorMessage,
  Loading,
  Pagination,
  Panel,
  SeveritySelect,
  Workspace,
  date,
  query,
  useData,
} from "../shared";
export default function Alerts() {
  const { scope, days } = useContext(Workspace);
  const [status, setStatus] = useState("");
  const [severity, setSeverity] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => setPage(1), [status, severity, scope, days]);
  const { data, error, loading } = useData<{ items: Alert[]; total: number }>(
    `/alerts?${query(scope, days)}&page=${page}${status ? "&status=" + status : ""}${severity ? "&severity=" + severity : ""}`,
  );
  return (
    <Panel
      title="Investigation queue"
      sub="Rule-based signals are not confirmed attacks"
    >
      <div className="filters">
        <div className="tabs">
          {["", "open", "investigating", "resolved"].map((x) => (
            <button
              className={status === x ? "active" : ""}
              key={x}
              onClick={() => setStatus(x)}
            >
              {x || "All alerts"}
            </button>
          ))}
        </div>
        <SeveritySelect value={severity} onChange={setSeverity} />
      </div>
      <ErrorMessage error={error} />
      {loading ? (
        <Loading />
      ) : data?.items.length ? (
        <>
          <div className="alert-list">
            {data.items.map((a) => (
              <NavLink className="alert-row" key={a.id} to={"/alerts/" + a.id}>
                <div className={`alert-symbol ${a.severity}`}>
                  <ShieldAlert size={23} />
                </div>
                <div className="alert-main">
                  <div>
                    <span className="mono">
                      {a.rule_id} / #{a.id}
                    </span>
                    <Badge value={a.severity} />
                  </div>
                  <h3>{a.description.split(":")[0]}</h3>
                  <p>
                    {a.subject} · {date(a.created_at)}
                  </p>
                </div>
                <Badge value={a.status} />
                <ChevronRight size={18} />
              </NavLink>
            ))}
          </div>
          <Pagination page={page} total={data.total} setPage={setPage} />
        </>
      ) : (
        <Empty text="No matching alerts." />
      )}
    </Panel>
  );
}
