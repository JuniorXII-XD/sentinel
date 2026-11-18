import { Search } from "lucide-react";
import { useContext, useEffect, useState } from "react";
import { type SecurityEvent } from "../api";

import {
  ErrorMessage,
  EventTable,
  Loading,
  Pagination,
  Panel,
  SeveritySelect,
  Workspace,
  label,
  query,
  useData,
} from "../shared";
export default function Events() {
  const { scope, days } = useContext(Workspace);
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [severity, setSeverity] = useState("");
  const [type, setType] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => {
    const id = setTimeout(() => setQ(search), 300);
    return () => clearTimeout(id);
  }, [search]);
  useEffect(() => setPage(1), [q, severity, type, scope, days]);
  const { data, error, loading } = useData<{
    items: SecurityEvent[];
    total: number;
  }>(
    `/events?${query(scope, days)}&q=${encodeURIComponent(q)}&severity=${severity}&event_type=${type}&page=${page}`.replace(
      "&severity=&",
      "&",
    ),
  );
  return (
    <Panel
      title="Event explorer"
      sub="Search by account, source IP or event type"
    >
      <div className="filters">
        <div className="search-field">
          <Search size={17} />
          <input
            aria-label="Search events"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search events, accounts or IPs…"
          />
        </div>
        <select
          aria-label="Event type"
          value={type}
          onChange={(e) => setType(e.target.value)}
        >
          <option value="">All event types</option>
          {[
            "login_success",
            "login_failed",
            "logout",
            "unauthorized_access",
            "suspicious_activity",
            "privilege_changed",
            "alert_updated",
            "rule_changed",
            "report_exported",
          ].map((x) => (
            <option key={x} value={x}>
              {label(x)}
            </option>
          ))}
        </select>
        <SeveritySelect value={severity} onChange={setSeverity} />
      </div>
      <ErrorMessage error={error} />
      {loading ? (
        <Loading />
      ) : (
        data && (
          <>
            <EventTable items={data.items} />
            <Pagination page={page} total={data.total} setPage={setPage} />
          </>
        )
      )}
    </Panel>
  );
}
