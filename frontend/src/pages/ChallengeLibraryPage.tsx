import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { get, api } from "../api/client";
import { useLoad } from "../hooks";
import { Button, Badge } from "../components/ui";
import { ErrorBox, Loading, Empty } from "../components/States";
import type { DailyChallenge, Option, ChallengeResult } from "../api/types";

function ChallengeItem({ challenge }: { challenge: DailyChallenge }) {
  const [choice, setChoice] = useState<Option | null>(null);
  const [result, setResult] = useState<ChallengeResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <article className="card question">
      <div className="row-between" style={{ marginBottom: 10 }}>
        <h2 style={{ fontSize: "1.2rem", margin: 0 }}>{challenge.title}</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <Badge variant="accent">{challenge.difficulty}</Badge>
          <span className="badge badge-primary">+{challenge.points} XP</span>
        </div>
      </div>

      <p className="muted small">{challenge.description}</p>

      <pre className="code" style={{ margin: "14px 0", padding: "14px", backgroundColor: "var(--code-bg)", color: "var(--code-text)" }}>
        <code>{challenge.code_snippet}</code>
      </pre>

      {challenge.has_completed && !result ? (
        <p className="sticky-note">
          <CheckCircle2 size={14} aria-hidden /> Completed in your profile. XP is awarded once per problem.
        </p>
      ) : (
        <>
          <fieldset disabled={busy || !!result} className="options">
            <legend className="sr-only">Choose your answer</legend>
            {(["A", "B", "C", "D"] as const).map((k) => (
              <label key={k} className={`option ${choice === k ? "chosen" : ""}`}>
                <input
                  type="radio"
                  name={challenge.id}
                  checked={choice === k}
                  onChange={() => setChoice(k)}
                />
                <span className="option-key">{k}</span>
                <code style={{ background: "transparent", border: "none", color: "inherit" }}>
                  {challenge[`option_${k.toLowerCase()}` as "option_a"]}
                </code>
              </label>
            ))}
          </fieldset>

          {error && <ErrorBox message={error} />}

          {result ? (
            <div
              className={`alert ${result.is_correct ? "alert-success" : "alert-error"}`}
              role="status"
              style={{ marginTop: 14 }}
            >
              <div>
                <strong>
                  {result.is_correct
                    ? `Correct! +${result.points_awarded} XP Awarded`
                    : "Incorrect. Review the explanation below."}
                </strong>
                <p style={{ margin: "4px 0 0", fontSize: "0.88rem" }}>{result.explanation}</p>
              </div>
            </div>
          ) : (
            <div style={{ marginTop: 14 }}>
              <Button
                variant="primary"
                size="sm"
                disabled={!choice}
                loading={busy}
                onClick={async () => {
                  if (!choice) return;
                  setBusy(true);
                  setError("");
                  try {
                    setResult(await api.submitChallenge(challenge.id, choice));
                  } catch (e) {
                    setError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Submit Answer
              </Button>
            </div>
          )}
        </>
      )}
    </article>
  );
}

export default function ChallengeLibraryPage() {
  const library = useLoad(() => get<DailyChallenge[]>("/challenges/library"));
  const [difficulty, setDifficulty] = useState("");

  if (library.loading) return <Loading label="Loading challenge library catalog…" />;
  if (library.error || !library.data)
    return <ErrorBox message={library.error ?? "Library unavailable"} onRetry={library.reload} />;

  const filtered = library.data.filter((c) => !difficulty || c.difficulty === difficulty);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">CHALLENGE VAULT // SELF-PACED DRILLS</div>
          <h1>CHALLENGE LIBRARY</h1>
          <p className="muted">
            Continuous puzzle solving beyond the daily drop. Master concepts, debug edge cases, and collect XP.
          </p>
        </div>
        <div>
          <label className="sr-only" htmlFor="diff-filter">Filter challenge difficulty</label>
          <select
            id="diff-filter"
            aria-label="Filter challenge difficulty"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
            style={{ minWidth: 180 }}
          >
            <option value="">All Difficulties</option>
            {Array.from(new Set(library.data.map((c) => c.difficulty))).map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </header>

      {library.data.length === 0 && <Empty title="No challenges available in the catalog" />}

      <div className="grid-2">
        {filtered.map((c) => (
          <ChallengeItem key={c.id} challenge={c} />
        ))}
      </div>
    </div>
  );
}
