import {
  ArrowRight,
  Award,
  ClipboardCheck,
  Flame,
  MessageSquare,
  Star,
  Swords,
  Target,
  Trophy,
  Zap,
} from "lucide-react";
import { api } from "../api/client";
import { navigate, useLoad } from "../hooks";
import { Button, ProgressBar } from "../components/ui";
import { Empty, ErrorBox, Loading, formatDate, levelClass } from "../components/States";

export default function DashboardPage() {
  const { data, error, loading, reload } = useLoad(api.dashboard);
  if (loading) return <Loading label="Initializing learning command center…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  const { user, selected_subject: subject, metrics: m } = data;
  const hasAttempts = m.total_assessments_completed > 0;

  // Journey checklist derived exclusively from stored records.
  const journey = [
    { label: "Create account", done: true },
    { label: "Engage with AI Mentor", done: m.chat_questions_asked > 0, path: "learn" },
    { label: "Choose learning subject", done: data.has_selected_subject, path: "subjects" },
    { label: "Complete diagnostics", done: hasAttempts, path: "assessment" },
    { label: "Solve daily challenge", done: m.challenges_attempted > 0, path: "challenge" },
  ];
  const journeyPct = Math.round((journey.filter((j) => j.done).length / journey.length) * 100);

  return (
    <div className="page">
      {/* Command Center Header */}
      <header className="page-head">
        <div>
          <div className="eyebrow">COMMAND CENTER // ACTIVE LEARNER</div>
          <h1>WELCOME BACK, {user.name.split(" ")[0].toUpperCase()}</h1>
          <p className="muted">
            {user.email} · Currently Mastering <strong style={{ color: "var(--text-primary)" }}>{subject.title}</strong>
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <Button
            variant="outline"
            leftIcon={MessageSquare}
            onClick={() => navigate("learn")}
          >
            AI Mentor
          </Button>
          <Button
            variant="primary"
            leftIcon={ClipboardCheck}
            onClick={() => navigate("learn")}
          >
            {hasAttempts ? "Continue Learning" : "Start Diagnostic"}
          </Button>
        </div>
      </header>

      {/* Editorial Statistics Grid */}
      <section className="stats" aria-label="Key performance metrics">
        <div className="stat card">
          <div className="row-between">
            <span className="stat-label">LATEST SCORE</span>
            <Target className="stat-icon" aria-hidden />
          </div>
          <span className="stat-value">
            {m.latest_score === null ? "—" : `${m.latest_score}/${m.latest_total}`}
          </span>
          <div style={{ marginTop: 4 }}>
            <span className={m.latest_score === null ? "muted small" : levelClass(m.latest_proficiency)}>
              {m.latest_score === null ? "Not attempted" : m.latest_proficiency}
            </span>
          </div>
        </div>

        <div className="stat card">
          <div className="row-between">
            <span className="stat-label">ASSESSMENTS</span>
            <ClipboardCheck className="stat-icon" aria-hidden />
          </div>
          <span className="stat-value">{m.total_assessments_completed}</span>
          <span className="muted small">
            Best <strong>{m.best_percentage}%</strong> · Avg {m.average_percentage}%
          </span>
        </div>

        <div className="stat card">
          <div className="row-between">
            <span className="stat-label">AI MENTOR DIALOGUES</span>
            <MessageSquare className="stat-icon" aria-hidden />
          </div>
          <span className="stat-value">{m.chat_questions_asked}</span>
          <span className="muted small">Questions answered</span>
        </div>

        <div className="stat card">
          <div className="row-between">
            <span className="stat-label">ARENA POINTS</span>
            <Flame className="stat-icon" style={{ color: "var(--color-amber)" }} aria-hidden />
          </div>
          <span className="stat-value">{m.total_points}</span>
          <span className="muted small">
            {data.badges.length} verified badge{data.badges.length === 1 ? "" : "s"}
          </span>
        </div>
      </section>

      {/* Primary Split: Journey vs Recommendations & Quick Actions */}
      <div className="grid-2">
        {/* Learning Journey & Progress */}
        <section className="card">
          <div className="row-between" style={{ marginBottom: 12 }}>
            <h2>LEARNING PROGRESSION</h2>
            <span className="badge badge-primary">{journeyPct}% COMPLETE</span>
          </div>
          <p className="muted small">Personal milestone trajectory for your active curriculum track.</p>
          <ProgressBar value={journeyPct} label="Learning journey progress" />

          <ul className="checklist">
            {journey.map((j) => (
              <li key={j.label} className={j.done ? "done" : ""}>
                <span className="check" aria-hidden>{j.done ? "✓" : ""}</span>
                <span style={{ flex: 1, fontWeight: j.done ? 500 : 700 }}>
                  {j.path && !j.done ? (
                    <a href={`#/${j.path}`}>{j.label}</a>
                  ) : (
                    j.label
                  )}
                </span>
                {j.done ? (
                  <span className="badge badge-success" style={{ fontSize: "0.65rem" }}>DONE</span>
                ) : (
                  <span className="badge" style={{ fontSize: "0.65rem" }}>PENDING</span>
                )}
              </li>
            ))}
          </ul>

          <div style={{ marginTop: 24, paddingTop: 16, borderTop: "1.5px dashed var(--border-strong)" }}>
            <div className="row-between" style={{ marginBottom: 6 }}>
              <span className="muted small" style={{ fontWeight: 700, textTransform: "uppercase" }}>Best Assessment Mastery</span>
              <span className="small" style={{ fontWeight: 800 }}>{m.best_percentage}%</span>
            </div>
            <ProgressBar value={m.best_percentage} label="Best assessment score" />
          </div>
        </section>

        {/* Recommended Topics & Arena Quick Launcher */}
        <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          <section className="card">
            <div className="row-between" style={{ marginBottom: 10 }}>
              <h2>RECOMMENDED FOCUS</h2>
              <span className="badge badge-accent">AI CURATED</span>
            </div>
            <p className="muted small">
              {data.recommendations_source === "latest_assessment"
                ? "Dynamically derived from the conceptual boundaries missed in your latest diagnostic."
                : "Starter foundation concepts. Complete a diagnostic assessment for personalized targets."}
            </p>
            <ul className="topics">
              {data.recommended_next_topics.map((t) => (
                <li key={t}>
                  <Star size={15} style={{ color: "var(--color-gold)" }} aria-hidden />
                  <span>{t}</span>
                </li>
              ))}
            </ul>
            <div style={{ marginTop: 16 }}>
              <Button
                variant="outline"
                size="sm"
                block
                rightIcon={ArrowRight}
                onClick={() => navigate("learn")}
              >
                Study Concepts with AI Mentor
              </Button>
            </div>
          </section>

          {/* Quick Arena Launch Card */}
          <section className="card" style={{ backgroundColor: "var(--color-plum-dark)", color: "#FFFFFF" }}>
            <div className="row-between" style={{ marginBottom: 8 }}>
              <h3 style={{ color: "var(--color-gold)", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                <Swords size={18} aria-hidden /> 1v1 CODE ARENA
              </h3>
              <span className="badge" style={{ backgroundColor: "var(--color-amber)", color: "#FFFFFF" }}>
                LIVE DUELS
              </span>
            </div>
            <p style={{ color: "#E2DDD4", fontSize: "0.88rem", margin: "6px 0 16px" }}>
              Challenge a fellow student to a synchronized timed 5-question code duel.
            </p>
            <div style={{ display: "flex", gap: 10 }}>
              <Button
                variant="primary"
                size="sm"
                leftIcon={Swords}
                onClick={() => navigate("battles")}
              >
                Enter Arena
              </Button>
              <Button
                variant="outline"
                size="sm"
                leftIcon={Zap}
                onClick={() => navigate("challenge")}
                style={{ backgroundColor: "transparent", color: "#FFFFFF", borderColor: "rgba(255,255,255,0.3)" }}
              >
                Daily Challenge
              </Button>
            </div>
          </section>
        </div>
      </div>

      {/* Recent Assessments Data Table */}
      <section className="card">
        <div className="row-between" style={{ marginBottom: 16 }}>
          <div>
            <h2>RECENT ASSESSMENTS</h2>
            <p className="muted small" style={{ margin: 0 }}>Objective server-evaluated testing history.</p>
          </div>
          {hasAttempts && (
            <a href="#/results" className="btn btn-outline btn-sm">
              View Complete History
            </a>
          )}
        </div>

        {!hasAttempts ? (
          <Empty title="No assessments completed yet">
            <p className="muted">Complete the diagnostic assessment to establish your proficiency baseline and unlock recommendations.</p>
            <div style={{ marginTop: 14 }}>
              <Button variant="primary" size="sm" onClick={() => navigate("learn")}>
                Start Diagnostic
              </Button>
            </div>
          </Empty>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Date & Time</th>
                  <th>Subject</th>
                  <th>Score</th>
                  <th>Proficiency Level</th>
                  <th style={{ textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_attempts.map((a) => (
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

      {/* Badges & Achievements */}
      {data.badges.length > 0 && (
        <section className="card">
          <div className="row-between" style={{ marginBottom: 16 }}>
            <h2>VERIFIED BADGES & ACHIEVEMENTS</h2>
            <a href="#/rewards" className="btn btn-ghost btn-sm">
              Rewards Ledger
            </a>
          </div>
          <div className="badges">
            {data.badges.map((b) => (
              <div key={b.id} className="badge-card">
                {b.icon === "zap" ? (
                  <Zap style={{ color: "var(--color-amber)" }} aria-hidden />
                ) : b.icon === "award" ? (
                  <Award style={{ color: "var(--color-plum-mid)" }} aria-hidden />
                ) : (
                  <Trophy style={{ color: "var(--color-gold)" }} aria-hidden />
                )}
                <div>
                  <strong style={{ display: "block", fontSize: "0.9rem" }}>{b.title}</strong>
                  <small className="muted">{b.description}</small>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
