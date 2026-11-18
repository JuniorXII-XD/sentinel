import {
  Activity,
  Check,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Shield,
} from "lucide-react";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, type SecurityEvent, type Summary, type User } from "./api";

export const Auth = createContext<{
  user: User | null;
  setUser: (x: User | null) => void;
  demo: boolean;
  setDemo: (x: boolean) => void;
}>({ user: null, setUser: () => {}, demo: false, setDemo: () => {} });
export const Workspace = createContext({ scope: "live", days: 7, revision: 0 });
export const colors: Record<string, string> = {
  critical: "#fb7185",
  high: "#fbbf24",
  medium: "#a78bfa",
  low: "#38d5eb",
};
export const label = (s: string) => s.replaceAll("_", " ");
export const date = (s: string) =>
  new Date(s).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
export const number = (n: number) => n.toLocaleString();
export const query = (scope: string, days: number) =>
  `scope=${scope}&days=${days}`;
export function Badge({ value }: { value: string }) {
  return (
    <span className={`badge ${value}`}>
      <i />
      {label(value)}
    </span>
  );
}

export function Empty({
  text = "No records in this view.",
}: {
  text?: string;
}) {
  return (
    <div className="empty">
      <Shield size={32} />
      <strong>{text}</strong>
      <span>Try another time range or data source.</span>
    </div>
  );
}

export function Loading() {
  return (
    <div role="status" className="loading">
      <RefreshCw className="spin" size={20} /> Loading secure workspace…
    </div>
  );
}

export function ErrorMessage({ error }: { error: string }) {
  return error ? (
    <div role="alert" className="error">
      {error}
    </div>
  ) : null;
}

export function useData<T>(path: string) {
  const { revision } = useContext(Workspace);
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    api<T>(path)
      .then((x) => {
        if (active) setData(x);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [path, revision, reload]);
  return { data, error, loading, refresh: () => setReload((x) => x + 1) };
}

export function Panel({
  title,
  sub,
  action,
  children,
  className = "",
}: {
  title: string;
  sub?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      <div className="panel-head">
        <div>
          <h2>{title}</h2>
          {sub && <p>{sub}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function Stat({
  title,
  value,
  icon: Icon,
  note,
  tone = "cyan",
}: {
  title: string;
  value: number | string;
  icon: typeof Shield;
  note: string;
  tone?: string;
}) {
  return (
    <div className="stat">
      <div className="stat-top">
        <span>{title}</span>
        <span className={`stat-icon ${tone}`}>
          <Icon size={18} />
        </span>
      </div>
      <strong>{typeof value === "number" ? number(value) : value}</strong>
      <small>
        <span className={`dot ${tone}`} />
        {note}
      </small>
    </div>
  );
}

export function EventTable({ items }: { items: SecurityEvent[] }) {
  return items.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Event / account</th>
            <th>Source IP</th>
            <th>Severity</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e) => (
            <tr key={e.id}>
              <td>
                <div className="event-name">
                  <span
                    className={`event-icon ${e.event_type === "login_success" ? "good" : "warn"}`}
                  >
                    {e.event_type === "login_success" ? (
                      <Check size={15} />
                    ) : (
                      <Activity size={15} />
                    )}
                  </span>
                  <div>
                    <strong>{label(e.event_type)}</strong>
                    <small>
                      {e.metadata.account ||
                        (e.user_id ? `User #${e.user_id}` : "System")}{" "}
                      <span className="muted">· #{e.id}</span>
                    </small>
                  </div>
                </div>
              </td>
              <td className="mono">{e.source_ip}</td>
              <td>
                <Badge value={e.severity} />
              </td>
              <td className="timestamp">{date(e.occurred_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty />
  );
}

export function Timeline({ data }: { data: Summary }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data.timeline}
          margin={{ top: 15, right: 8, left: -24, bottom: 0 }}
        >
          <defs>
            <linearGradient id="cyan" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#33d1e4" stopOpacity={0.24} />
              <stop offset="100%" stopColor="#33d1e4" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            vertical={false}
            stroke="#253045"
            strokeDasharray="3 5"
          />
          <XAxis
            dataKey="date"
            tickFormatter={(x) => x.slice(5)}
            axisLine={false}
            tickLine={false}
            minTickGap={28}
          />
          <YAxis axisLine={false} tickLine={false} allowDecimals={false} />
          <Tooltip
            contentStyle={{
              background: "#121b2c",
              border: "1px solid #334155",
              borderRadius: 10,
            }}
          />
          <Area
            type="monotone"
            dataKey="success"
            name="Successful login"
            stroke="#33d1e4"
            strokeWidth={2.5}
            fill="url(#cyan)"
          />
          <Area
            type="monotone"
            dataKey="failed"
            name="Failed login"
            stroke="#b18aff"
            strokeWidth={2}
            fill="#a78bfa"
            fillOpacity={0.06}
          />
          <Area
            type="monotone"
            dataKey="other"
            name="Other events"
            stroke="#fbbf24"
            fill="none"
            strokeWidth={1.5}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SeverityChart({ data }: { data: Summary }) {
  const values = ["critical", "high", "medium", "low"].map((k) => ({
    name: k,
    value: data.severity[k] || 0,
  }));
  return (
    <div className="severity-layout">
      <div className="donut">
        <ResponsiveContainer width="100%" height={190}>
          <PieChart>
            <Pie
              data={values}
              innerRadius={62}
              outerRadius={79}
              paddingAngle={5}
              dataKey="value"
              stroke="none"
            >
              {values.map((x) => (
                <Cell key={x.name} fill={colors[x.name]} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "#121b2c",
                border: "1px solid #334155",
                borderRadius: 8,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <strong>{data.total_alerts}</strong>
          <span>Total alerts</span>
        </div>
      </div>
      <div className="severity-legend">
        {values.map((x) => (
          <div key={x.name}>
            <span>
              <i style={{ background: colors[x.name] }} />
              {x.name}
            </span>
            <strong>{x.value}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

export function Pagination({
  page,
  total,
  setPage,
}: {
  page: number;
  total: number;
  setPage: (x: number) => void;
}) {
  return (
    <div className="pagination">
      <span>
        {number(total)} records · Page {page} of{" "}
        {Math.max(1, Math.ceil(total / 20))}
      </span>
      <div>
        <button
          className="icon-btn bordered"
          aria-label="Previous page"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
        >
          <ChevronLeft size={17} />
        </button>
        <button
          className="icon-btn bordered"
          aria-label="Next page"
          disabled={page * 20 >= total}
          onClick={() => setPage(page + 1)}
        >
          <ChevronRight size={17} />
        </button>
      </div>
    </div>
  );
}

export function SeveritySelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (x: string) => void;
}) {
  return (
    <select
      aria-label="Severity"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    >
      <option value="">All severities</option>
      {Object.keys(colors).map((x) => (
        <option key={x} value={x}>
          {x}
        </option>
      ))}
    </select>
  );
}
