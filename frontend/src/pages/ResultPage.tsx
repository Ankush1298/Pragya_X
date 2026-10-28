import { ArrowRight, CircleCheck, CircleX, LayoutDashboard, MessageSquare, RotateCcw, Star } from "lucide-react";
import { api } from "../api/client";
import { DemoBadge, ErrorBox, Loading, ProgressBar, formatDate, levelClass } from "../components/States";
import { Button, Badge } from "../components/ui";
import { navigate, useLoad } from "../hooks";

export default function ResultPage({ id }: { id: string }) {
  const { data: r, error, loading, reload } = useLoad(() => api.attempt(id), [id]);

  if (loading) return <Loading label="Calculating assessment feedback…" />;
  if (error || !r)
    return (
      <div className="page narrow">
        <ErrorBox message={error ?? "Result record not found"} onRetry={reload} />
        <Button variant="ghost" onClick={() => navigate("results")}>
          ← Back to Assessment History
        </Button>
      </div>
    );

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <div className="eyebrow">EVALUATION REPORT // VERIFIED SERVER SCORE</div>
          <h1>ASSESSMENT RESULTS</h1>
          <p className="muted">
            {r.subject_title} · Completed on {formatDate(r.created_at)} · Permanently logged to your profile
          </p>
        </div>
        {r.is_mock && <DemoBadge label="Mock Evaluator" />}
      </header>

      {/* Main Score Hero Card */}
      <section className="card score-card" style={{ border: "3px solid var(--border-strong)", boxShadow: "var(--shadow-lg)" }}>
        <div className="score-ring">
          <span className="score-num">
            {r.score}
            <small>/{r.total}</small>
          </span>
        </div>
        <div className="score-body">
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className={levelClass(r.proficiency_level)} style={{ fontSize: "0.85rem", padding: "4px 10px" }}>
              {r.proficiency_level.toUpperCase()}
            </span>
            <span className="badge badge-primary">{r.percentage}% ACCURACY</span>
          </div>
          <p className="score-pct">{r.percentage}%</p>
          <ProgressBar value={r.percentage} label="Score percentage" />
          <p style={{ margin: "8px 0 0", fontSize: "1rem", lineHeight: 1.5 }}>{r.summary_feedback}</p>
          <p className="muted small" style={{ margin: "4px 0 0" }}>
            Benchmark: 0–2 correct = Beginner · 3–4 = Intermediate · 5 = Advanced. Evaluated by {r.provider}.
          </p>
        </div>
      </section>

      {/* Recommended Next Topics */}
      <section className="card">
        <div className="row-between" style={{ marginBottom: 12 }}>
          <h2>RECOMMENDED NEXT TOPICS</h2>
          <span className="badge badge-accent">PERSONALIZED TARGETS</span>
        </div>
        <p className="muted small">
          Focus on these conceptual targets to improve proficiency for your next evaluation attempt.
        </p>
        <ul className="topics">
          {r.recommended_topics.map((t) => (
            <li key={t}>
              <Star size={16} style={{ color: "var(--color-gold)" }} aria-hidden />
              <span>{t}</span>
            </li>
          ))}
        </ul>
        <div style={{ marginTop: 14 }}>
          <Button
            variant="outline"
            size="sm"
            leftIcon={MessageSquare}
            onClick={() => navigate("learn")}
          >
            Study These Topics with AI Mentor
          </Button>
        </div>
      </section>

      {/* Question-by-Question Feedback */}
      <section>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>DETAILED QUESTION FEEDBACK</h2>
          <span className="badge">{(r.breakdown ?? []).length} QUESTIONS</span>
        </div>
        {r.breakdown.map((b, i) => (
          <article
            key={b.question_id}
            className={`card feedback ${b.is_correct ? "ok" : "bad"}`}
            style={{ marginBottom: 16 }}
          >
            <div className="row-between" style={{ marginBottom: 8 }}>
              <strong>
                {b.is_correct ? (
                  <CircleCheck size={18} className="ok-icon" style={{ verticalAlign: "middle", marginRight: 6 }} aria-hidden />
                ) : (
                  <CircleX size={18} className="bad-icon" style={{ verticalAlign: "middle", marginRight: 6 }} aria-hidden />
                )}
                QUESTION {i + 1} · {b.is_correct ? "CORRECT (+1)" : "INCORRECT (0)"}
              </strong>
              <Badge variant={b.is_correct ? "success" : "error"}>{b.topic}</Badge>
            </div>

            <pre className="question-text">{b.question_text}</pre>

            <div style={{ margin: "10px 0", fontSize: "0.95rem" }}>
              <span>Your Answer: </span>
              <strong style={{ color: b.is_correct ? "var(--color-success)" : "var(--color-error)" }}>
                Choice {b.selected_option}
              </strong>
              {!b.is_correct && (
                <>
                  {" "}· Official Correct Choice:{" "}
                  <strong style={{ color: "var(--color-success)" }}>Choice {b.correct_option}</strong>
                </>
              )}
            </div>

            <div className="explain">
              <strong style={{ display: "block", fontSize: "0.82rem", textTransform: "uppercase", marginBottom: 2 }}>
                Conceptual Explanation:
              </strong>
              <span>{b.explanation}</span>
            </div>
          </article>
        ))}
      </section>

      {/* Bottom Actions */}
      <div className="actions" style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 8 }}>
        <Button
          variant="primary"
          onClick={() => navigate("dashboard")}
          leftIcon={LayoutDashboard}
          rightIcon={ArrowRight}
        >
          Return to Dashboard
        </Button>
        <Button
          variant="accent"
          onClick={() => navigate("learn")}
          leftIcon={MessageSquare}
        >
          Study Weak Topics with Mentor
        </Button>
        <Button
          variant="outline"
          onClick={() => navigate("assessment")}
          leftIcon={RotateCcw}
        >
          Retake Assessment
        </Button>
      </div>
    </div>
  );
}
