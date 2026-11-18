import {
  Activity,
  ArrowUpRight,
  CheckCheck,
  Fingerprint,
  Radio,
  ShieldAlert,
} from "lucide-react";
import { useContext } from "react";
import { NavLink } from "react-router-dom";
import { type Alert, type SecurityEvent, type Summary } from "../api";

import {
  Badge,
  Empty,
  ErrorMessage,
  EventTable,
  Loading,
  Panel,
  SeverityChart,
  Stat,
  Timeline,
  Workspace,
  number,
  query,
  useData,
} from "../shared";
export default function Overview() {
  const { scope, days } = useContext(Workspace);
  const qs = query(scope, days);
  const { data, error, loading } = useData<Summary>("/overview?" + qs);
  const ev = useData<{ items: SecurityEvent[] }>(
    "/events?" + qs + "&page_size=5",
  );
  const al = useData<{ items: Alert[] }>(
    "/alerts?" + qs + "&status=open&page_size=3",
  );
  if (loading) return <Loading />;
  if (error || !data) return <ErrorMessage error={error} />;
  const successRate =
    data.login_success + data.login_failed
      ? Math.round(
          (data.login_success / (data.login_success + data.login_failed)) * 100,
        )
      : 0;
  return (
    <>
      <div className="overview-notice">
        <span className="notice-icon">
          <Radio size={19} />
        </span>
        <div>
          <strong>
            {data.active_alerts
              ? `${data.active_alerts} signals awaiting review`
              : "Your workspace is ready"}
          </strong>
          <span>
            {data.active_alerts
              ? "Review active alerts and verify their context before taking action."
              : "New security events will appear here as users interact with the system."}
          </span>
        </div>
        <NavLink to="/alerts">
          Open alert queue <ArrowUpRight size={15} />
        </NavLink>
      </div>
      <div className="stats-grid">
        <Stat
          title="Total security events"
          value={data.total_events}
          icon={Activity}
          note={`Across the last ${days} days`}
        />
        <Stat
          title="Active alerts"
          value={data.active_alerts}
          icon={ShieldAlert}
          note="Open + investigating"
          tone="purple"
        />
        <Stat
          title="High-risk events"
          value={data.high_risk_events}
          icon={Fingerprint}
          note="High + critical event severity"
          tone="amber"
        />
        <Stat
          title="Login success rate"
          value={`${successRate}%`}
          icon={CheckCheck}
          note={`${number(data.login_success)} successful sign-ins`}
          tone="green"
        />
      </div>
      <div className="charts-grid">
        <Panel
          title="Authentication activity"
          sub="Successful and failed login events over time"
          action={
            <div className="chart-key">
              <span>
                <i className="dot cyan" />
                Success
              </span>
              <span>
                <i className="dot purple" />
                Failed
              </span>
            </div>
          }
        >
          <Timeline data={data} />
        </Panel>
        <Panel title="Alert severity" sub="All alerts in the selected period">
          <SeverityChart data={data} />
        </Panel>
      </div>
      <div className="bottom-grid">
        <Panel
          title="Recent security events"
          sub="The latest activity in your workspace"
          action={
            <NavLink className="text-link" to="/events">
              View all <ArrowUpRight size={14} />
            </NavLink>
          }
        >
          <EventTable items={ev.data?.items || []} />
          <ErrorMessage error={ev.error} />
        </Panel>
        <Panel
          title="Needs attention"
          sub="Open alerts · Newest first"
          action={<ShieldAlert className="muted" size={18} />}
        >
          {al.data?.items.length ? (
            <div className="attention-list">
              {al.data.items.map((a) => (
                <NavLink key={a.id} to={"/alerts/" + a.id}>
                  <div>
                    <Badge value={a.severity} />
                    <small className="mono">
                      #{String(a.id).padStart(4, "0")}
                    </small>
                  </div>
                  <strong>
                    {a.rule_id === "AUTH-001"
                      ? "Repeated login failures"
                      : a.rule_id === "AUTH-002"
                        ? "Password spraying pattern"
                        : a.rule_id === "AUTH-003"
                          ? "Multiple-account failures"
                          : a.rule_id === "ACCESS-001"
                            ? "Restricted privilege access"
                            : "Unusual login time"}
                  </strong>
                  <span>
                    {a.subject}
                    <ArrowUpRight size={15} />
                  </span>
                </NavLink>
              ))}
            </div>
          ) : (
            <Empty text="No open alerts." />
          )}
          <ErrorMessage error={al.error} />
        </Panel>
      </div>
    </>
  );
}
