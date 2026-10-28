import { ClipboardCheck } from "lucide-react";
import { api } from "../api/client";
import { Empty, ErrorBox, Loading, formatDate, levelClass } from "../components/States";
import { Button } from "../components/ui";
import { navigate, useLoad } from "../hooks";

export default function HistoryPage() {
  const { data, error, loading, reload } = useLoad(api.history);
  if (loading) return <Loading label="Loading assessment history…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">ASSESSMENT ARCHIVES // RECORDED SCORES</div>
          <h1>MY RESULTS & ASSESSMENTS</h1>
          <p className="muted">
            Every completed diagnostic and assessment is permanently logged to your account with breakdown evaluations.
          </p>
        </div>
        <Button variant="primary" leftIcon={ClipboardCheck} onClick={() => navigate("assessment")}>
          Take New Assessment
        </Button>
      </header>

      <section className="card">
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>COMPLETED ATTEMPTS</h2>
          <span className="badge badge-primary">{data.attempts.length} ATTEMPTS</span>
        </div>

        {data.attempts.length === 0 ? (
          <Empty title="No assessment records found">
            <p className="muted small">Complete the 5-question Python diagnostic to establish your initial score history.</p>
            <div style={{ marginTop: 14 }}>
              <Button variant="primary" onClick={() => navigate("assessment")}>
                Take First Assessment
              </Button>
            </div>
          </Empty>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Completed Date</th>
                  <th>Subject</th>
                  <th>Score Ratio</th>
                  <th>Proficiency Level</th>
                  <th style={{ textAlign: "right" }}>Detailed Review</th>
                </tr>
              </thead>
              <tbody>
                {data.attempts.map((a) => (
                  <tr key={a.id}>
                    <td>{formatDate(a.created_at)}</td>
                    <td><strong>{a.subject_title}</strong></td>
                    <td>
                      <strong>{a.score}/{a.total}</strong>{" "}
                      <span className="muted small">({a.percentage}%)</span>
                    </td>
                    <td>
                      <span className={levelClass(a.proficiency_level)}>
                        {a.proficiency_level}
                      </span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <a href={`#/result/${a.id}`} className="btn btn-outline btn-sm">
                        Review Feedback
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
