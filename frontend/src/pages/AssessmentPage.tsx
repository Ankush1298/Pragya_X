import { useState } from "react";
import { ArrowLeft, ArrowRight, CircleCheck, Send } from "lucide-react";
import { api } from "../api/client";
import type { Option, Question } from "../api/types";
import { DemoBadge, ErrorBox, Loading } from "../components/States";
import { Button, Badge } from "../components/ui";
import { navigate, useLoad } from "../hooks";

const OPTIONS: Option[] = ["A", "B", "C", "D"];
const optionText = (q: Question, o: Option) => q[`option_${o.toLowerCase()}` as "option_a"];

async function loadAssessment() {
  const { subjects, selected_subject_id } = await api.subjects();
  const subject = subjects.find((s) => s.id === selected_subject_id) ?? subjects[0];
  const questions = await api.questions(subject.id);
  return { subject, questions };
}

export default function AssessmentPage() {
  const { data, error, loading, reload } = useLoad(loadAssessment);
  const [step, setStep] = useState(0); // 0..4 questions, 5 = review
  const [answers, setAnswers] = useState<Record<string, Option>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  if (loading) return <Loading label="Loading diagnostic assessment…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  const { subject, questions } = data;
  const total = questions.length;
  const answered = questions.filter((q) => answers[q.id]).length;
  const isReview = step === total;
  const q = questions[step];

  const submit = async () => {
    if (answered < total || submitting) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const result = await api.submitAssessment(subject.id, answers);
      navigate(`result/${result.id}`);
    } catch (e) {
      setSubmitError((e as Error).message);
      setSubmitting(false);
    }
  };

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <div className="eyebrow">DIAGNOSTIC ENGINE // {subject.title.toUpperCase()}</div>
          <h1>{subject.title.toUpperCase()} ASSESSMENT</h1>
          <p className="muted">
            {total} focused questions · Graded strictly on the server <DemoBadge label="Mock Evaluation" />
          </p>
        </div>
      </header>

      {/* Stepper Navigation */}
      <ol className="stepper" aria-label="Assessment progress">
        {questions.map((qq, i) => (
          <li key={qq.id}>
            <button
              className={`step ${i === step ? "current" : ""} ${answers[qq.id] ? "answered" : ""}`}
              onClick={() => setStep(i)}
              aria-label={`Question ${i + 1}${answers[qq.id] ? ", answered" : ""}`}
              aria-current={i === step ? "step" : undefined}
            >
              {answers[qq.id] ? <CircleCheck size={16} aria-hidden /> : i + 1}
            </button>
          </li>
        ))}
        <li>
          <button
            className={`step step-review ${isReview ? "current" : ""}`}
            onClick={() => setStep(total)}
            aria-current={isReview ? "step" : undefined}
          >
            Review ({answered}/{total})
          </button>
        </li>
      </ol>

      {!isReview ? (
        <section className="card question">
          <div className="row-between" style={{ marginBottom: 12 }}>
            <span className="badge badge-primary">
              QUESTION {step + 1} OF {total}
            </span>
            <Badge variant="accent">{q.topic}</Badge>
          </div>

          <pre className="question-text">{q.question_text}</pre>

          <fieldset className="options">
            <legend className="sr-only">Choose one answer</legend>
            {OPTIONS.map((o) => (
              <label key={o} className={`option ${answers[q.id] === o ? "chosen" : ""}`}>
                <input
                  type="radio"
                  name={q.id}
                  value={o}
                  checked={answers[q.id] === o}
                  onChange={() => setAnswers({ ...answers, [q.id]: o })}
                />
                <span className="option-key">{o}</span>
                <span>{optionText(q, o)}</span>
              </label>
            ))}
          </fieldset>

          <div className="row-between" style={{ marginTop: 20 }}>
            <Button
              variant="ghost"
              disabled={step === 0}
              onClick={() => setStep(step - 1)}
              leftIcon={ArrowLeft}
            >
              Previous
            </Button>
            <Button
              variant="primary"
              disabled={!answers[q.id]}
              onClick={() => setStep(step + 1)}
              rightIcon={ArrowRight}
            >
              {step === total - 1 ? "Review Answers" : "Next Question"}
            </Button>
          </div>
        </section>
      ) : (
        <section className="card">
          <div className="row-between" style={{ marginBottom: 12 }}>
            <h2>REVIEW YOUR RESPONSES</h2>
            <Badge variant={answered === total ? "success" : "warning"}>
              {answered}/{total} COMPLETED
            </Badge>
          </div>
          <p className="muted small">
            Verify your answers before final grading. Submissions are permanently saved to your verified skill history.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 10, margin: "18px 0" }}>
            {questions.map((qq, i) => (
              <div
                key={qq.id}
                className="row-between"
                style={{
                  padding: "12px 16px",
                  border: "2px solid var(--border-strong)",
                  boxShadow: "var(--shadow-sm)",
                  borderRadius: "var(--radius-xs)",
                  backgroundColor: answers[qq.id] ? "#FFFFFF" : "#FEF3C7",
                }}
              >
                <div>
                  <button
                    className="link"
                    onClick={() => setStep(i)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: 0,
                      fontWeight: 800,
                      fontFamily: "var(--font-heading)",
                      fontSize: "0.95rem",
                      textAlign: "left",
                    }}
                  >
                    Q{i + 1}. {qq.topic}
                  </button>
                  <p className="muted small" style={{ margin: "2px 0 0" }}>
                    {qq.question_text.slice(0, 70)}…
                  </p>
                </div>
                <span className={answers[qq.id] ? "badge badge-primary" : "badge badge-warn"}>
                  {answers[qq.id] ? `OPTION ${answers[qq.id]}` : "NOT ANSWERED"}
                </span>
              </div>
            ))}
          </div>

          {submitError && <ErrorBox message={submitError} />}

          <Button
            variant="primary"
            size="lg"
            block
            disabled={answered < total || submitting}
            loading={submitting}
            onClick={submit}
            leftIcon={Send}
          >
            {submitting
              ? "Grading on Server…"
              : answered < total
              ? `Answer all ${total} questions to submit (${answered} completed)`
              : "Submit for Official Evaluation"}
          </Button>
        </section>
      )}
    </div>
  );
}
