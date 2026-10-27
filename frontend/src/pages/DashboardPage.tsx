import { ArrowRight, Award, ClipboardCheck, Flame, MessageSquare, Star, Target, Trophy, Zap } from "lucide-react";
import { api } from "../api/client";
import { navigate, useLoad } from "../hooks";
import { Empty, ErrorBox, Loading, ProgressBar, formatDate, levelClass } from "../components/States";

export default function DashboardPage() {
  const { data, error, loading, reload } = useLoad(api.dashboard);
  if (loading) return <Loading label="Loading your dashboard…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  const { user, selected_subject: subject, metrics: m } = data;
  const hasAttempts = m.total_assessments_completed > 0;

  // Journey checklist is derived only from stored records.
  const journey = [
    { label: "Create account", done: true },
    { label: "Ask the learning chat", done: m.chat_questions_asked > 0, path: "learn" },
    { label: "Choose a subject", done: data.has_selected_subject, path: "subjects" },
    { label: "Complete an assessment", done: hasAttempts, path: "assessment" },
    { label: "Solve the daily challenge", done: m.challenges_attempted > 0, path: "challenge" },
  ];
  const journeyPct = Math.round((journey.filter((j) => j.done).length / journey.length) * 100);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Welcome back, {user.name.split(" ")[0]}</h1>
          <p className="muted">
            {user.email} · Learning <strong>{subject.title}</strong>
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate("learn")}>
          <ClipboardCheck size={16} aria-hidden /> {hasAttempts ? "Retake assessment" : "Take assessment"}
        </button>
      </header>

      <section className="stats">
        <div className="stat card">
          <Target className="stat-icon" aria-hidden />
          <span className="stat-label">Latest score</span>
          <span className="stat-value">{m.latest_score === null ? "—" : `${m.latest_score}/${m.latest_total}`}</span>
          <span className={m.latest_score === null ? "muted small" : levelClass(m.latest_proficiency)}>{m.latest_proficiency}</span>
        </div>
        <div className="stat card">
          <ClipboardCheck className="stat-icon" aria-hidden />
          <span className="stat-label">Assessments completed</span>
          <span className="stat-value">{m.total_assessments_completed}</span>
          <span className="muted small">Best {m.best_percentage}% · Avg {m.average_percentage}%</span>
        </div>
        <div className="stat card">
          <MessageSquare className="stat-icon" aria-hidden />
          <span className="stat-label">Questions asked</span>
          <span className="stat-value">{m.chat_questions_asked}</span>
          <span className="muted small">in Learning Chat</span>
        </div>
        <div className="stat card">
          <Flame className="stat-icon" aria-hidden />
          <span className="stat-label">Points</span>
          <span className="stat-value">{m.total_points}</span>
          <span className="muted small">{data.badges.length} badge{data.badges.length === 1 ? "" : "s"} earned</span>
        </div>
      </section>

      <div className="grid-2">
        <section className="card">
          <h2>Learning progress</h2>
          <p className="muted small">Your journey: {journeyPct}% complete</p>
          <ProgressBar value={journeyPct} label="Learning journey progress" />
          <ul className="checklist">
            {journey.map((j) => (
              <li key={j.label} className={j.done ? "done" : ""}>
                <span className="check" aria-hidden>{j.done ? "✓" : ""}</span>
                {j.path && !j.done ? <a href={`#/${j.path}`}>{j.label}</a> : j.label}
              </li>
            ))}
          </ul>
          <div className="mastery">
            <span className="muted small">Best assessment mastery</span>
            <ProgressBar value={m.best_percentage} label="Best assessment score" />
          </div>
        </section>

        <section className="card">
          <h2>Recommended next topics</h2>
          <p className="muted small">
            {data.recommendations_source === "latest_assessment"
              ? "Based on the questions you missed in your latest assessment."
              : "Starter topics. Take the assessment for personalised recommendations."}
          </p>
          <ul className="topics">
            {data.recommended_next_topics.map((t) => (
              <li key={t}>
                <Star size={15} aria-hidden /> {t}
              </li>
            ))}
          </ul>
          <button className="btn btn-ghost" onClick={() => navigate("learn")}>
            Study with Learning Chat <ArrowRight size={15} aria-hidden />
          </button>
        </section>
      </div>

      <section className="card">
        <div className="row-between">
          <h2>Recent assessments</h2>
          {hasAttempts && <a href="#/results">View all</a>}
        </div>
        {!hasAttempts ? (
          <Empty title="No assessments yet">
            <p className="muted">Complete the 5-question Python assessment to see your score history here.</p>
          </Empty>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Date</th><th>Subject</th><th>Score</th><th>Level</th><th></th></tr>
            </thead>
            <tbody>
              {data.recent_attempts.map((a) => (
                <tr key={a.id}>
                  <td>{formatDate(a.created_at)}</td>
                  <td>{a.subject_title}</td>
                  <td><strong>{a.score}/{a.total}</strong> <span className="muted">({a.percentage}%)</span></td>
                  <td><span className={levelClass(a.proficiency_level)}>{a.proficiency_level}</span></td>
                  <td><a href={`#/result/${a.id}`}>Review</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {data.badges.length > 0 && (
        <section className="card">
          <h2>Badges</h2>
          <div className="badges">
            {data.badges.map((b) => (
              <div key={b.id} className="badge-card">
                {b.icon === "zap" ? <Zap aria-hidden /> : b.icon === "award" ? <Award aria-hidden /> : <Trophy aria-hidden />}
                <div>
                  <strong>{b.title}</strong>
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
