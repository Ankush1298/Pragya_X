import { useState } from "react";
import { Award, CircleCheck, CircleX, Zap } from "lucide-react";
import { api } from "../api/client";
import type { ChallengeResult, Option } from "../api/types";
import { ErrorBox, Loading } from "../components/States";
import { Button, Badge } from "../components/ui";
import { navigate, useLoad } from "../hooks";

const OPTIONS: Option[] = ["A", "B", "C", "D"];

export default function ChallengePage() {
  const { data: c, error, loading, reload } = useLoad(api.dailyChallenge);
  const [choice, setChoice] = useState<Option | null>(null);
  const [result, setResult] = useState<ChallengeResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  if (loading) return <Loading label="Loading today's code breaker challenge…" />;
  if (error || !c) return <ErrorBox message={error ?? "No active challenge found"} onRetry={reload} />;

  const submit = async () => {
    if (!choice) return;
    setBusy(true);
    setSubmitError(null);
    try {
      setResult(await api.submitChallenge(c.id, choice));
    } catch (e) {
      setSubmitError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  // Either this session's result or the stored submission from an earlier visit.
  const done =
    result ??
    (c.has_completed && c.user_submission
      ? {
          is_correct: !!c.user_submission.is_correct,
          points_awarded: c.user_submission.points_awarded,
          correct_option: c.correct_option ?? "",
          explanation: c.explanation ?? "",
        }
      : null);
  const picked = result ? choice : (c.user_submission?.submitted_answer as Option | undefined) ?? choice;

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <div className="eyebrow">DAILY ARENA // CODE BREAKER</div>
          <h1 style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Zap size={26} style={{ color: "var(--color-amber)" }} aria-hidden /> DAILY CODE CHALLENGE
          </h1>
          <p className="muted">
            One question per day to forge your streak. Correct answers earn <strong>+{c.points} XP</strong> and unlock the verified Daily Code Breaker badge.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate("library")}>
          Challenge Library
        </Button>
      </header>

      <section className="card question" style={{ border: "2px solid var(--border-strong)", boxShadow: "var(--shadow-lg)" }}>
        <div className="row-between" style={{ marginBottom: 12 }}>
          <strong style={{ fontSize: "1.2rem", fontFamily: "var(--font-heading)" }}>{c.title}</strong>
          <div style={{ display: "flex", gap: 8 }}>
            <Badge variant="accent">{c.difficulty}</Badge>
            <span className="badge badge-primary">+{c.points} XP</span>
          </div>
        </div>

        <p style={{ fontSize: "0.98rem", lineHeight: 1.5 }}>{c.description}</p>

        <pre className="code" style={{ margin: "16px 0", padding: "16px", backgroundColor: "var(--code-bg)", color: "var(--code-text)" }}>
          <code>{c.code_snippet}</code>
        </pre>

        <fieldset className="options" disabled={!!done || busy}>
          <legend className="sr-only">Choose one answer</legend>
          {OPTIONS.map((o) => {
            const isChosen = picked === o;
            const isCorrect = done && o === done.correct_option;
            const isWrong = done && isChosen && !done.is_correct;
            const cls = isCorrect ? "chosen" : isWrong ? "chosen" : isChosen ? "chosen" : "";

            return (
              <label
                key={o}
                className={`option ${cls}`}
                style={{
                  borderColor: isCorrect
                    ? "var(--color-success)"
                    : isWrong
                    ? "var(--color-error)"
                    : undefined,
                  backgroundColor: isCorrect
                    ? "#DCFCE7"
                    : isWrong
                    ? "#FEE2E2"
                    : undefined,
                }}
              >
                <input
                  type="radio"
                  name="challenge"
                  checked={picked === o}
                  onChange={() => setChoice(o)}
                />
                <span className="option-key">{o}</span>
                <code style={{ fontSize: "0.92rem", background: "transparent", border: "none", color: "inherit" }}>
                  {c[`option_${o.toLowerCase()}` as "option_a"]}
                </code>
              </label>
            );
          })}
        </fieldset>

        {submitError && <ErrorBox message={submitError} />}

        {done ? (
          <div
            className={`alert ${done.is_correct ? "alert-success" : "alert-error"}`}
            role="status"
            style={{ marginTop: 20 }}
          >
            {done.is_correct ? (
              <CircleCheck size={20} aria-hidden />
            ) : (
              <CircleX size={20} aria-hidden />
            )}
            <div>
              <strong style={{ fontSize: "1.05rem" }}>
                {done.is_correct
                  ? `Correct! +${done.points_awarded} XP Awarded to Ledger`
                  : "Not quite. Challenge recorded without penalty."}
              </strong>
              {done.is_correct && (
                <p style={{ margin: "4px 0 8px", display: "flex", alignItems: "center", gap: 6 }}>
                  <Award size={15} style={{ color: "var(--color-gold)" }} aria-hidden />
                  <span>Achievement: Daily Code Breaker</span>
                </p>
              )}
              <p style={{ margin: "6px 0 0", fontSize: "0.9rem" }}>{done.explanation}</p>
            </div>
          </div>
        ) : (
          <div style={{ marginTop: 20 }}>
            <Button
              variant="primary"
              size="lg"
              block
              disabled={!choice || busy}
              loading={busy}
              onClick={submit}
            >
              Submit Daily Answer
            </Button>
          </div>
        )}
      </section>
    </div>
  );
}
