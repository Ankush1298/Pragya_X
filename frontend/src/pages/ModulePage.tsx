import { useState } from "react";
import { ArrowLeft, ArrowRight, CircleCheck, CircleX, RotateCcw } from "lucide-react";
import { learn, type Practice } from "../api/learn";
import Markdown from "../components/Markdown";
import { Badge, Button, Card } from "../components/ui";
import { ErrorBox, Loading } from "../components/States";
import { navigate, useLoad } from "../hooks";

export default function ModulePage({ chatId, moduleId }: { chatId?: string; moduleId?: string }) {
  const cid = chatId ?? "";
  const mid = moduleId ?? "";
  const { data, error, loading, reload } = useLoad(() => learn.module(cid, mid), [cid, mid]);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [result, setResult] = useState<Practice | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (!chatId || !moduleId)
    return (
      <div className="page narrow">
        <ErrorBox message="Please open a lesson directly from your learning chat roadmap." />
        <Button variant="ghost" onClick={() => navigate("learn")}>
          ← Go to Learning Chats
        </Button>
      </div>
    );

  if (loading) return <Loading label="Loading lesson & practical drills…" />;
  if (error || !data)
    return (
      <div className="page narrow">
        <ErrorBox message={error ?? "Lesson unavailable"} onRetry={reload} />
        <Button variant="ghost" leftIcon={ArrowLeft} onClick={() => navigate("learn", cid)}>
          Back to Chat Workspace
        </Button>
      </div>
    );

  const qs = data.questions;
  const answered = qs.filter((q) => answers[q.id] !== undefined).length;

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      setResult(await learn.practice(cid, mid, answers));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const retry = () => {
    setAnswers({});
    setResult(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <div className="eyebrow">CURRICULUM LESSON // {data.module.difficulty.toUpperCase()}</div>
          <h1>{data.module.title.toUpperCase()}</h1>
          <p className="muted">
            {data.module.difficulty} · ~{data.module.estimated_minutes} min read{" "}
            {data.module.status === "completed" && <span className="badge badge-success">COMPLETED ✓</span>}
          </p>
        </div>
        <Button variant="outline" leftIcon={ArrowLeft} onClick={() => navigate("learn", cid)}>
          Back to Roadmap
        </Button>
      </header>

      {/* Lesson Content */}
      <Card className="lesson" style={{ border: "2px solid var(--border-strong)", boxShadow: "var(--shadow-md)" }}>
        <Markdown text={data.lesson} />
      </Card>

      {/* Practice Drills Section */}
      <section style={{ marginTop: 24 }}>
        <div className="row-between" style={{ marginBottom: 12 }}>
          <h2>PRACTICE DRILLS</h2>
          <span className="badge badge-accent">SERVER GRADED</span>
        </div>
        <p className="muted small">
          {data.pass_rule}. Answers and step-by-step explanations are revealed once submitted.
        </p>

        {!result &&
          qs.map((q, i) => (
            <section key={q.id} className="card question" style={{ marginBottom: 16 }}>
              <div className="row-between" style={{ marginBottom: 8 }}>
                <span className="muted small">Question {i + 1} of {qs.length}</span>
                <Badge>{q.difficulty}</Badge>
              </div>
              <p className="question-text" style={{ whiteSpace: "pre-wrap" }}>
                {q.question}
              </p>
              <fieldset className="options">
                <legend className="sr-only">Choose one answer</legend>
                {q.options.map((o, k) => (
                  <label key={k} className={`option ${answers[q.id] === k ? "chosen" : ""}`}>
                    <input
                      type="radio"
                      name={q.id}
                      checked={answers[q.id] === k}
                      onChange={() => setAnswers({ ...answers, [q.id]: k })}
                    />
                    <span className="option-key">{"ABCD"[k]}</span>
                    <span>{o}</span>
                  </label>
                ))}
              </fieldset>
            </section>
          ))}

        {!result && (
          <div style={{ marginTop: 20 }}>
            {err && <ErrorBox message={err} />}
            <Button
              variant="primary"
              size="lg"
              block
              loading={busy}
              disabled={answered < qs.length}
              onClick={submit}
              rightIcon={ArrowRight}
            >
              {answered < qs.length ? `Answer all questions (${answered}/${qs.length})` : "Submit Practice Answers"}
            </Button>
          </div>
        )}

        {/* Practice Result Screen */}
        {result && (
          <div style={{ marginTop: 20 }}>
            <div
              className={`callout ${result.passed ? "" : "callout-limit"}`}
              style={{ padding: 24, border: "3px solid var(--border-strong)", boxShadow: "var(--shadow-lg)" }}
              role="status"
            >
              <div>
                <strong style={{ fontSize: "1.3rem", fontFamily: "var(--font-display)" }}>
                  {result.passed ? "MODULE MASTERED! 🎉" : "REVIEW & RETRY"}
                </strong>
                <p style={{ margin: "6px 0 0" }}>
                  Score: <strong>{result.correct}/{result.total}</strong> ({result.percentage}%).
                  {result.passed ? " Module marked as completed in your roadmap." : " Minimum score required to pass."}
                </p>
              </div>
              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 8 }}>
                <Button variant="primary" onClick={() => navigate("learn", cid)}>
                  Return to Roadmap
                </Button>
                <Button variant="outline" leftIcon={RotateCcw} onClick={retry}>
                  Retry Practice
                </Button>
              </div>
            </div>

            <h3 style={{ marginTop: 24, textTransform: "uppercase" }}>Question Review & Explanations</h3>
            {result.feedback.map((f, i) => (
              <Card
                key={f.question_id}
                className={`question ${f.is_correct ? "fb right" : "fb wrong"}`}
                style={{
                  marginBottom: 14,
                  borderLeft: f.is_correct ? "6px solid var(--color-success)" : "6px solid var(--color-error)",
                }}
              >
                <div className="row-between" style={{ marginBottom: 6 }}>
                  <strong>
                    {f.is_correct ? (
                      <CircleCheck size={16} className="ok-icon" aria-hidden />
                    ) : (
                      <CircleX size={16} className="bad-icon" aria-hidden />
                    )}{" "}
                    Question {i + 1}: {f.is_correct ? "Correct" : "Incorrect"}
                  </strong>
                </div>
                <p style={{ fontWeight: 600 }}>{f.question}</p>
                <div style={{ margin: "6px 0", fontSize: "0.92rem" }}>
                  <span>Your answer: <strong>{f.options[f.selected_index]}</strong></span>
                  {!f.is_correct && (
                    <span> · Correct: <strong style={{ color: "var(--color-success)" }}>{f.options[f.correct_index]}</strong></span>
                  )}
                </div>
                <p className="explain">{f.explanation}</p>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
