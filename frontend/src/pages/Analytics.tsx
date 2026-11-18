import {
  ChartNoAxesCombined,
  Check,
  CheckCheck,
  LockKeyhole,
} from "lucide-react";
import { useContext } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { type Summary } from "../api";

import {
  ErrorMessage,
  Loading,
  Panel,
  SeverityChart,
  Stat,
  Timeline,
  Workspace,
  label,
  query,
  useData,
} from "../shared";
export default function Analytics() {
  const { scope, days } = useContext(Workspace);
  const { data, error, loading } = useData<Summary>(
    "/overview?" + query(scope, days),
  );
  if (loading) return <Loading />;
  if (error || !data) return <ErrorMessage error={error} />;
  return (
    <>
      <div className="stats-grid">
        <Stat
          title="Successful logins"
          value={data.login_success}
          icon={Check}
          note="Authenticated sessions"
          tone="green"
        />
        <Stat
          title="Failed logins"
          value={data.login_failed}
          icon={LockKeyhole}
          note="Rejected credentials"
          tone="amber"
        />
        <Stat
          title="Resolved alerts"
          value={data.resolved_alerts}
          icon={CheckCheck}
          note="Investigation completed"
        />
        <Stat
          title="Resolution rate"
          value={`${data.resolution_rate}%`}
          icon={ChartNoAxesCombined}
          note="Resolved / all alerts in period"
          tone="purple"
        />
      </div>
      <Panel title="Event timeline" sub="Daily totals · UTC">
        <Timeline data={data} />
      </Panel>
      <div className="charts-grid">
        <Panel title="Event distribution" sub="Frequency by event type">
          <div className="chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={Object.entries(data.event_types).map(([name, value]) => ({
                  name: label(name),
                  value,
                }))}
                margin={{ left: -20, right: 24, bottom: 28 }}
              >
                <CartesianGrid vertical={false} stroke="#253045" />
                <XAxis
                  dataKey="name"
                  fontSize={10}
                  interval={0}
                  angle={-12}
                  textAnchor="end"
                />
                <YAxis allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    background: "#121b2c",
                    border: "1px solid #334155",
                  }}
                />
                <Bar dataKey="value" fill="#9d82f5" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="Risk profile" sub="Severity of rule-generated alerts">
          <SeverityChart data={data} />
        </Panel>
      </div>
    </>
  );
}
