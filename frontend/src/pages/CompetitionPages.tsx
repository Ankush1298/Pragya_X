import { useState, type FormEvent } from "react";
import { Medal, Plus, Trophy } from "lucide-react";
import { comps, growth, battles, type Comp } from "../api/learn";
import { useLoad, navigate } from "../hooks";
import { Button, Badge } from "../components/ui";
import { ErrorBox, Loading, Empty, formatDate } from "../components/States";

type DraftQuestion = {
  question_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  correct_option: string;
  explanation: string;
  topic: string;
};

const emptyQuestion = (): DraftQuestion => ({
  question_text: "",
  option_a: "",
  option_b: "",
  option_c: "",
  option_d: "",
  correct_option: "A",
  explanation: "",
  topic: "General",
});

function QuestionEditor({
  questions,
  onChange,
}: {
  questions: DraftQuestion[];
  onChange: (questions: DraftQuestion[]) => void;
}) {
  const update = (index: number, key: keyof DraftQuestion, value: string) =>
    onChange(questions.map((q, i) => (i === index ? { ...q, [key]: value } : q)));

  return (
    <section style={{ margin: "16px 0" }}>
      <h3 style={{ textTransform: "uppercase", fontSize: "0.95rem" }}>Competition Questions ({questions.length}/20)</h3>
      {questions.map((q, i) => (
        <fieldset
          className="card"
          key={i}
          style={{ marginBottom: 16, backgroundColor: "#FAF9F5" }}
        >
          <legend style={{ fontWeight: 800, fontFamily: "var(--font-heading)" }}>
            QUESTION {i + 1}
          </legend>
          <label className="field">
            <span>Question Prompt</span>
            <textarea
              required
              rows={3}
              value={q.question_text}
              onChange={(e) => update(i, "question_text", e.target.value)}
              placeholder="e.g. What will be the output of the following Python expression?"
            />
          </label>
          <div className="grid-2">
            {(["option_a", "option_b", "option_c", "option_d"] as const).map((key, j) => (
              <label className="field" key={key}>
                <span>Choice {String.fromCharCode(65 + j)}</span>
                <input
                  required
                  value={q[key]}
                  onChange={(e) => update(i, key, e.target.value)}
                  placeholder={`Option ${String.fromCharCode(65 + j)} text`}
                />
              </label>
            ))}
          </div>
          <div className="grid-2">
            <label className="field">
              <span>Correct Choice</span>
              <select
                value={q.correct_option}
                onChange={(e) => update(i, "correct_option", e.target.value)}
              >
                {["A", "B", "C", "D"].map((k) => (
                  <option key={k} value={k}>
                    Choice {k}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Conceptual Topic</span>
              <input
                value={q.topic}
                onChange={(e) => update(i, "topic", e.target.value)}
                placeholder="e.g. Scope (LEGB), Comprehensions"
              />
            </label>
          </div>
          <label className="field">
            <span>Explanation & Solution</span>
            <textarea
              required
              rows={2}
              value={q.explanation}
              onChange={(e) => update(i, "explanation", e.target.value)}
              placeholder="Explanation revealed to contestants after submission"
            />
          </label>
          {questions.length > 1 && (
            <div style={{ marginTop: 8 }}>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onChange(questions.filter((_, j) => i !== j))}
              >
                Remove Question {i + 1}
              </Button>
            </div>
          )}
        </fieldset>
      ))}
      <Button
        variant="outline"
        size="sm"
        disabled={questions.length >= 20}
        onClick={() => onChange([...questions, emptyQuestion()])}
        leftIcon={Plus}
      >
        Add Another Question
      </Button>
    </section>
  );
}

/* ------------------------------------------------------------------ Leaderboards */
export function LeaderboardsPage() {
  const challenge = useLoad(growth.challengeLeaderboard);
  const battle = useLoad(battles.leaderboard);

  if (challenge.loading || battle.loading) return <Loading label="Loading leaderboards…" />;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">GLOBAL ARENA // RANKINGS</div>
          <h1>LEADERBOARDS & STANDINGS</h1>
          <p className="muted">Verified rankings earned exclusively by registered PragyaX learners through server evaluation.</p>
        </div>
      </header>

      <div className="grid-2">
        <section className="card">
          <div className="row-between" style={{ marginBottom: 14 }}>
            <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
              <Trophy size={20} style={{ color: "var(--color-gold)" }} aria-hidden /> CHALLENGE POINTS
            </h2>
            <Badge variant="primary">DAILY & LIBRARY</Badge>
          </div>
          {challenge.error && <ErrorBox message={challenge.error} onRetry={challenge.reload} />}
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 60 }}>#</th>
                  <th>Gladiator</th>
                  <th style={{ textAlign: "right" }}>Total Points</th>
                </tr>
              </thead>
              <tbody>
                {(challenge.data ?? []).map((x, i) => (
                  <tr key={x.user_id}>
                    <td>
                      <span
                        className="badge"
                        style={{
                          backgroundColor: i === 0 ? "var(--color-gold)" : i === 1 ? "var(--bg-secondary)" : "#FFFFFF",
                          color: i === 0 ? "var(--color-plum-dark)" : "var(--text-primary)",
                          fontWeight: 800,
                        }}
                      >
                        #{i + 1}
                      </span>
                    </td>
                    <td><strong>{x.display_name ?? x.name ?? "Learner"}</strong></td>
                    <td style={{ textAlign: "right" }}>
                      <span className="badge badge-primary">{x.total_points} PTS</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {challenge.data?.length === 0 && <Empty title="Be the first to complete a challenge" />}
        </section>

        <section className="card">
          <div className="row-between" style={{ marginBottom: 14 }}>
            <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
              <Medal size={20} style={{ color: "var(--color-amber)" }} aria-hidden /> 1v1 BATTLE WINS
            </h2>
            <Badge variant="accent">LIVE DUELS</Badge>
          </div>
          {battle.error && <ErrorBox message={battle.error} onRetry={battle.reload} />}
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 60 }}>#</th>
                  <th>Gladiator</th>
                  <th>Record (W-L-T)</th>
                  <th style={{ textAlign: "right" }}>Wins</th>
                </tr>
              </thead>
              <tbody>
                {(battle.data ?? []).map((x, i) => (
                  <tr key={x.user_id}>
                    <td>
                      <span
                        className="badge"
                        style={{
                          backgroundColor: i === 0 ? "var(--color-plum-dark)" : i === 1 ? "var(--bg-secondary)" : "#FFFFFF",
                          color: i === 0 ? "#FFFFFF" : "var(--text-primary)",
                          fontWeight: 800,
                        }}
                      >
                        #{i + 1}
                      </span>
                    </td>
                    <td><strong>{x.name}</strong></td>
                    <td><span className="muted small">{x.wins}W · {x.losses}L · {x.ties}T</span></td>
                    <td style={{ textAlign: "right" }}>
                      <span className="pill-ok" style={{ fontWeight: 800 }}>{x.wins} WINS</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {battle.data?.length === 0 && <Empty title="No completed battles yet" />}
        </section>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ Competitions Page */
export function CompetitionsPage({ id }: { id?: string }) {
  return id ? <CompetitionDetail key={id} id={id} /> : <CompetitionHub />;
}

function CompetitionHub() {
  const list = useLoad(comps.list);
  const orgs = useLoad(comps.orgs);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [org, setOrg] = useState("");
  const [questions, setQuestions] = useState<DraftQuestion[]>([emptyQuestion()]);

  const create = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      const comp = await comps.create({
        org_id: org,
        title: String(f.get("title")),
        description: String(f.get("description")),
        subject_id: "subj_python",
        difficulty: "Intermediate",
        start_time: new Date(String(f.get("start"))).toISOString(),
        end_time: new Date(String(f.get("end"))).toISOString(),
        questions,
      });
      navigate("competitions", comp.id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const registerOrg = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setBusy(true);
    setError("");
    try {
      await comps.createOrg({
        name: String(f.get("name")),
        org_type: String(f.get("type")),
        description: String(f.get("description")),
      });
      setNotice("Organization registered. College and company hosts require platform verification before scheduling.");
      orgs.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">TOURNAMENTS // COMMUNITY & CAMPUS</div>
          <h1>HOSTED COMPETITIONS</h1>
          <p className="muted">Learn and compete together through student, college, and company-sponsored challenges.</p>
        </div>
      </header>

      {error && <ErrorBox message={error} />}
      {notice && <p role="status" className="sticky-note">{notice}</p>}

      {list.loading ? (
        <Loading label="Loading competitions…" />
      ) : list.error ? (
        <ErrorBox message={list.error} onRetry={list.reload} />
      ) : (
        <div className="grid-2">
          {list.data?.map((c) => (
            <article className="card" key={c.id}>
              <div className="row-between" style={{ marginBottom: 10 }}>
                <Badge variant={c.host_type === "COMPANY" ? "accent" : c.host_type === "COLLEGE" ? "primary" : "default"}>
                  {c.host_type} HOSTED
                </Badge>
                <span
                  className="badge"
                  style={{
                    backgroundColor: c.status === "ACTIVE" ? "var(--color-amber)" : c.status === "COMPLETED" ? "var(--bg-secondary)" : "#FEF3C7",
                    color: c.status === "ACTIVE" ? "#FFFFFF" : "var(--text-primary)",
                    fontWeight: 800,
                  }}
                >
                  {c.status}
                </span>
              </div>
              <h2 style={{ fontSize: "1.3rem" }}>{c.title}</h2>
              <p className="muted" style={{ minHeight: 44 }}>{c.description}</p>
              <div style={{ margin: "14px 0", fontSize: "0.85rem" }} className="muted">
                📅 <strong>{formatDate(c.start_time)}</strong> – <strong>{formatDate(c.end_time)}</strong>
              </div>
              <Button
                variant={c.status === "ACTIVE" ? "primary" : "outline"}
                block
                onClick={() => navigate("competitions", c.id)}
              >
                {c.status === "ACTIVE" ? "Enter Competition" : "View Competition Details"}
              </Button>
            </article>
          ))}
          {list.data?.length === 0 && <Empty title="No competitions scheduled yet" />}
        </div>
      )}

      {/* Host a competition collapse */}
      <details className="card" style={{ marginTop: 24 }}>
        <summary style={{ cursor: "pointer", fontFamily: "var(--font-heading)", fontWeight: 800, fontSize: "1.1rem" }}>
          ORGANIZER PORTAL: HOST A COMPETITION / REGISTER ORGANIZATION
        </summary>
        <div className="grid-2" style={{ marginTop: 20 }}>
          <form onSubmit={registerOrg} className="card" style={{ backgroundColor: "#FAF9F5" }}>
            <h2>REGISTER ORGANIZATION</h2>
            <p className="muted small">Host student tournaments under your university or company brand.</p>
            <label className="field">
              <span>Organization Name</span>
              <input name="name" required placeholder="e.g. Stanford ACM, Acme Corp" />
            </label>
            <label className="field">
              <span>Host Classification</span>
              <select name="type">
                <option value="STUDENT">STUDENT CHAPTER</option>
                <option value="COLLEGE">COLLEGE / UNIVERSITY</option>
                <option value="COMPANY">COMPANY / INDUSTRY SPONSOR</option>
              </select>
            </label>
            <label className="field">
              <span>Description</span>
              <textarea name="description" required rows={3} placeholder="About your club or organization" />
            </label>
            <Button type="submit" variant="secondary" loading={busy}>
              Register Host
            </Button>
          </form>

          <form onSubmit={create} className="card" style={{ backgroundColor: "#FAF9F5" }}>
            <h2>SCHEDULE TOURNAMENT</h2>
            {orgs.error && <ErrorBox message={orgs.error} onRetry={orgs.reload} />}
            <label className="field">
              <span>Hosting Organization</span>
              <select required value={org} onChange={(e) => setOrg(e.target.value)}>
                <option value="">Select your registered organization</option>
                {orgs.data?.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name} {o.is_verified ? "· Verified ✓" : "· Pending Verification"}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Tournament Title</span>
              <input required name="title" placeholder="e.g. Winter Python Invitational 2026" />
            </label>
            <label className="field">
              <span>Description</span>
              <textarea required name="description" rows={2} placeholder="Rules, topics covered, and eligibility" />
            </label>
            <div className="grid-2">
              <label className="field">
                <span>Start Window</span>
                <input required type="datetime-local" name="start" />
              </label>
              <label className="field">
                <span>End Window</span>
                <input required type="datetime-local" name="end" />
              </label>
            </div>
            <QuestionEditor questions={questions} onChange={setQuestions} />
            <Button type="submit" variant="primary" loading={busy}>
              Create Competition
            </Button>
          </form>
        </div>
      </details>
    </div>
  );
}

function CompetitionDetail({ id }: { id: string }) {
  const c = useLoad(() => comps.one(id), [id]);
  const rankings = useLoad(() => comps.leaderboard(id), [id]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [result, setResult] = useState("");
  const [busy, setBusy] = useState(false);
  const [start] = useState(Date.now());
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      c.reload();
      rankings.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (c.loading) return <Loading label="Loading competition arena…" />;
  if (c.error || !c.data)
    return <ErrorBox message={c.error ?? "Competition unavailable"} onRetry={c.reload} />;

  const comp: Comp = c.data;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">COMPETITION // {comp.status}</div>
          <h1>{comp.title.toUpperCase()}</h1>
          <p className="muted">{comp.description}</p>
          <div style={{ marginTop: 8 }}>
            <span className="badge badge-primary">{comp.status}</span> ·{" "}
            <span className="muted small">
              {formatDate(comp.start_time)} – {formatDate(comp.end_time)}
            </span>
          </div>
        </div>
        <Button variant="ghost" onClick={() => navigate("competitions")}>
          ← All Competitions
        </Button>
      </header>

      {comp.status === "SCHEDULED" && (
        <div className="callout" role="note">
          <div>
            <strong>Tournament Scheduled</strong>
            You are enrolled. Competition questions will automatically unlock when the official start window opens.
          </div>
        </div>
      )}

      {error && <ErrorBox message={error} />}
      {result && <p role="status" className="sticky-note">{result}</p>}

      {/* User result if submitted */}
      {comp.user_submission ? (
        <section className="card score-card">
          <div className="score-ring">
            <span className="score-num">
              {comp.user_submission.score}
              <small>/{comp.user_submission.total_questions}</small>
            </span>
          </div>
          <div className="score-body">
            <span className="badge badge-success">SUBMISSION COMPLETE</span>
            <p className="score-pct">{comp.user_submission.percentage}%</p>
            <p className="muted small">Your answers have been evaluated and locked into official tournament standings.</p>
          </div>
        </section>
      ) : (
        comp.status === "ACTIVE" && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act(async () => {
                const r = await comps.submit(id, answers, (Date.now() - start) / 1000);
                setResult(`${r.score}/${r.total_questions} correct · ${r.xp_awarded} XP awarded`);
              });
            }}
          >
            {comp.questions?.map((q, idx) => (
              <fieldset className="card question" key={q.id} style={{ marginBottom: 16 }}>
                <legend style={{ fontWeight: 800, fontFamily: "var(--font-heading)" }}>
                  QUESTION {idx + 1}
                </legend>
                <pre className="question-text">{q.question_text}</pre>
                <div className="options">
                  {(["A", "B", "C", "D"] as const).map((k) => (
                    <label key={k} className={`option ${answers[q.id] === k ? "chosen" : ""}`}>
                      <input
                        required
                        type="radio"
                        name={q.id}
                        value={k}
                        checked={answers[q.id] === k}
                        onChange={() => setAnswers({ ...answers, [q.id]: k })}
                      />
                      <span className="option-key">{k}</span>
                      <span>{q[`option_${k.toLowerCase()}` as "option_a"]}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
            ))}
            <Button type="submit" variant="primary" size="lg" loading={busy}>
              Submit Tournament Answers
            </Button>
          </form>
        )
      )}

      {/* Official Standings */}
      <section className="card">
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>OFFICIAL TOURNAMENT STANDINGS</h2>
          <span className="badge badge-accent">RANKED LEADERBOARD</span>
        </div>
        {rankings.error && <ErrorBox message={rankings.error} />}
        <div style={{ overflowX: "auto" }}>
          <table className="table">
            <thead>
              <tr>
                <th style={{ width: 60 }}>Rank</th>
                <th>Contestant</th>
                <th style={{ textAlign: "right" }}>Percentage Score</th>
              </tr>
            </thead>
            <tbody>
              {rankings.data?.map((r, i) => (
                <tr key={i}>
                  <td>
                    <span
                      className="badge"
                      style={{
                        backgroundColor: i === 0 ? "var(--color-gold)" : i === 1 ? "var(--bg-secondary)" : "#FFFFFF",
                        color: i === 0 ? "var(--color-plum-dark)" : "var(--text-primary)",
                        fontWeight: 800,
                      }}
                    >
                      #{i + 1}
                    </span>
                  </td>
                  <td><strong>{r.user_name}</strong></td>
                  <td style={{ textAlign: "right" }}>
                    <span className="badge badge-primary">{r.percentage}%</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rankings.data?.length === 0 && <p className="muted">No submissions recorded yet.</p>}
      </section>

      {/* Organizer Controls */}
      <details className="card">
        <summary style={{ cursor: "pointer", fontFamily: "var(--font-heading)", fontWeight: 800 }}>
          ORGANIZER CONTROLS & DASHBOARD
        </summary>
        <p className="muted small" style={{ marginTop: 8 }}>Available strictly to this competition's organizer and platform administrators.</p>
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", margin: "14px 0" }}>
          <Button
            size="sm"
            variant="outline"
            loading={busy}
            onClick={() => act(async () => setDashboard(await comps.dashboard(id)))}
          >
            Load Analytics Dashboard
          </Button>
          <Button
            size="sm"
            variant="primary"
            loading={busy}
            onClick={() =>
              act(async () => {
                await comps.announce(id);
                setResult("Winners announced. Eligible certificates issued.");
              })
            }
          >
            Conclude & Issue Certificates
          </Button>
        </div>
        {dashboard && (
          <section style={{ marginTop: 14, paddingTop: 14, borderTop: "1.5px dashed var(--border-strong)" }}>
            <h3>Competition Analytics</h3>
            <div className="stats">
              {Object.entries((dashboard.analytics ?? {}) as Record<string, number>).map(([k, v]) => (
                <div key={k} className="stat card">
                  <span className="stat-label">{k.replaceAll("_", " ")}</span>
                  <span className="stat-value" style={{ fontSize: "2rem" }}>{v}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </details>
    </div>
  );
}

/* ------------------------------------------------------------------ Admin Page */
export function AdminPage() {
  const analytics = useLoad(growth.adminAnalytics);
  const orgs = useLoad(comps.orgs);
  const [error, setError] = useState("");

  if (analytics.loading) return <Loading label="Loading administration…" />;
  if (analytics.error)
    return <ErrorBox message={analytics.error} onRetry={analytics.reload} />;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">ADMINISTRATION // SECURE ROLES</div>
          <h1>PLATFORM ADMINISTRATION</h1>
          <p className="muted">Server permissions verify access to administrative functions and organization approval.</p>
        </div>
      </header>

      <section className="card">
        <h2>PLATFORM ANALYTICS</h2>
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {Object.entries(analytics.data ?? {}).map(([group, values]) => (
            <div key={group}>
              <h3 style={{ textTransform: "uppercase", fontSize: "0.95rem", color: "var(--color-purple)" }}>
                {group}
              </h3>
              <div className="stats" style={{ marginTop: 8 }}>
                {Object.entries(values).map(([k, v]) => (
                  <div key={k} className="stat card">
                    <span className="stat-label">{k.replaceAll("_", " ")}</span>
                    <span className="stat-value" style={{ fontSize: "1.8rem" }}>{v}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>ORGANIZATION VERIFICATION</h2>
        {error && <ErrorBox message={error} />}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 14 }}>
          {orgs.data?.map((o) => (
            <div
              className="row-between"
              key={o.id}
              style={{
                padding: "12px 16px",
                border: "2px solid var(--border-strong)",
                boxShadow: "var(--shadow-sm)",
                borderRadius: "var(--radius-xs)",
              }}
            >
              <div>
                <strong>{o.name}</strong> · <span className="badge">{o.org_type}</span>
                <p className="muted small" style={{ margin: "2px 0 0" }}>
                  Status: {o.is_verified ? "Verified Host ✓" : "Pending Verification"}
                </p>
              </div>
              <Button
                size="sm"
                variant={o.is_verified ? "outline" : "primary"}
                onClick={async () => {
                  try {
                    await growth.adminVerifyOrg(o.id, !o.is_verified);
                    orgs.reload();
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                {o.is_verified ? "Revoke Verification" : "Approve & Verify Host"}
              </Button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
