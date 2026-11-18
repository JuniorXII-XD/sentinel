import {
  Activity,
  ArrowUpRight,
  CheckCheck,
  Clock3,
  Download,
  FileText,
  ShieldAlert,
} from "lucide-react";
import { useContext, useState } from "react";
import { api, type Summary } from "../api";

import {
  ErrorMessage,
  Loading,
  Panel,
  Stat,
  Workspace,
  date,
  query,
  useData,
} from "../shared";
export default function Reports() {
  const { scope, days } = useContext(Workspace);
  const { data, error, loading } = useData<Summary>(
    "/reports/summary?" + query(scope, days),
  );
  const [busy, setBusy] = useState("");
  const [exportError, setExportError] = useState("");
  async function download(format: string) {
    setBusy(format);
    setExportError("");
    try {
      const blob = await api<Blob>(
        `/reports/export?${query(scope, days)}&format=${format}`,
        { method: "POST" },
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `sentinel-${scope}-${days}d.${format}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e: any) {
      setExportError(e.message);
    } finally {
      setBusy("");
    }
  }
  if (loading) return <Loading />;
  if (error || !data) return <ErrorMessage error={error} />;
  return (
    <>
      <div className="report-hero">
        <div className="report-symbol">
          <FileText size={36} />
        </div>
        <div>
          <span className="eyebrow">
            SECURITY BRIEFING / {scope.toUpperCase()}
          </span>
          <h2>Your security activity, explained.</h2>
          <p>
            A database-backed summary for the last {days} days.
            <br />
            Generated {date(data.generated_at)}.
          </p>
        </div>
        <div className="report-actions">
          <button
            disabled={!!busy}
            className="button primary"
            onClick={() => download("pdf")}
          >
            <Download size={16} />
            {busy === "pdf" ? "Generating…" : "Export PDF"}
          </button>
          <button
            disabled={!!busy}
            className="button secondary"
            onClick={() => download("csv")}
          >
            <Download size={16} />
            {busy === "csv" ? "Generating…" : "Export CSV"}
          </button>
        </div>
      </div>
      <ErrorMessage error={exportError} />
      <div className="stats-grid">
        <Stat
          title="Events reviewed"
          value={data.total_events}
          icon={Activity}
          note="Selected period"
        />
        <Stat
          title="Risk signals"
          value={data.total_alerts}
          icon={ShieldAlert}
          note="All alert severities"
          tone="purple"
        />
        <Stat
          title="Resolved"
          value={data.resolved_alerts}
          icon={CheckCheck}
          note="Documented outcomes"
          tone="green"
        />
        <Stat
          title="Pending review"
          value={data.active_alerts}
          icon={Clock3}
          note="Open + investigating"
          tone="amber"
        />
      </div>
      <Panel
        title="Recommended next steps"
        sub="Recommendations based on the selected report"
      >
        <div className="recommendations">
          {data.recommendations.map((r, i) => (
            <div key={r}>
              <span>{String(i + 1).padStart(2, "0")}</span>
              <p>{r}</p>
              <ArrowUpRight size={18} />
            </div>
          ))}
        </div>
      </Panel>
      <p className="footnote">
        CSV includes summary, trends and up to 10,000 recent events. PDF
        includes summary, trends, severity, resolution and recommendations.
        Exports are audited.
      </p>
    </>
  );
}
