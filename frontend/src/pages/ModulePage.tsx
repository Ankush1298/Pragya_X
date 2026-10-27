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

  if (!chatId || !moduleId) return <ErrorBox message="Open a lesson from your roadmap." />;
  if (loading) return <Loading label="Opening lesson…" />;
  if (error || !data) return (
    <div className="page"><ErrorBox message={error ?? "Lesson unavailable"} onRetry={reload} />
      <Button variant="ghost" leftIcon={ArrowLeft} onClick={() => navigate("learn", cid)}>Back to chat</Button></div>
  );

  const qs = data.questions;
  const answered = qs.filter((q) => answers[q.id] !== undefined).length;
  const submit = async () => {
    setBusy(true); setErr(null);
    try { setResult(await learn.practice(cid, mid, answers)); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  const retry = () => { setAnswers({}); setResult(null); window.scrollTo({ top: 0, behavior: "smooth" }); };

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <p className="eyebrow">Lesson</p>
          <h1>{data.module.title}</h1>
          <p className="muted">{data.module.difficulty} · about {data.module.estimated_minutes} min {data.module.status === "completed" && <Badge variant="success">Completed</Badge>}</p>
        </div>
        <Button variant="ghost" leftIcon={ArrowLeft} onClick={() => navigate("learn", cid)}>Roadmap</Button>
      </header>

      <Card className="lesson">
        <Markdown text={data.lesson} />
      </Card>

      <h2 style={{ marginTop: 24 }}>Practice</h2>
      <p className="muted">{data.pass_rule} Graded on the server. Answers are revealed after you submit.</p>

      {!result && qs.map((q, i) => (
        <section key={q.id} className="card question" style={{ marginBottom: 14 }}>
          <div className="row-between"><span className="muted small">Question {i + 1} of {qs.length}</span><Badge>{q.difficulty}</Badge></div>
          <p className="question-text" style={{ whiteSpace: "pre-wrap" }}>{q.question}</p>
          <fieldset className="options">
            <legend className="sr-only">Choose one answer</legend>
            {q.options.map((o, k) => (
              <label key={k} className={`option ${answers[q.id] === k ? "chosen" : ""}`}>
                <input type="radio" name={q.id} checked={answers[q.id] === k} onChange={() => setAnswers({ ...answers, [q.id]: k })} />
                <span className="option-key">{"ABCD"[k]}</span><span>{o}</span>
              </label>
            ))}
          </fieldset>
        </section>
      ))}

      {!result && (
        <>
          {err && <ErrorBox message={err} />}
          <Button loading={busy} disabled={answered < qs.length} onClick={submit} rightIcon={ArrowRight}>
            {answered < qs.length ? `Answer all ${qs.length} (${answered} done)` : "Submit practice"}
          </Button>
        </>
      )}

      {result && (
        <>
          <div className={`callout ${result.passed ? "" : "callout-limit"}`} role="status">
            <div>
              <strong>{result.correct}/{result.total} correct ({result.percentage}%)</strong>
              {result.message}{result.xp_awarded > 0 && ` +${result.xp_awarded} XP`}
            </div>
            {result.passed
              ? <Button variant="accent" rightIcon={ArrowRight} onClick={() => navigate("learn", cid)}>Back to roadmap</Button>
              : <Button variant="accent" leftIcon={RotateCcw} onClick={retry}>Try again</Button>}
          </div>
          {result.feedback.map((f, i) => (
            <Card key={f.question_id} className="question">
              <strong>{i + 1}. {f.question}</strong>
              <div className={`fb ${f.is_correct ? "right" : "wrong"}`}>
                {f.is_correct ? <CircleCheck size={16} aria-hidden /> : <CircleX size={16} aria-hidden />} Your answer: {f.options[f.selected_index]}
              </div>
              {!f.is_correct && <div className="fb right">Correct: {f.options[f.correct_index]}</div>}
              <p className="muted small">{f.explanation}</p>
            </Card>
          ))}
        </>
      )}
    </div>
  );
}
