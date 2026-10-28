import { useEffect, useRef, useState } from "react";
import { Check, RefreshCw, Swords, X } from "lucide-react";
import { battles, type BattleView, type Invitation } from "../api/learn";
import { Badge, Button, Card } from "../components/ui";
import { Empty, ErrorBox, Loading, formatDate } from "../components/States";
import { navigate, useLoad } from "../hooks";

/** Polling keeps things honest and reliable: no websocket service is claimed. */
function usePoll<T>(fn: () => Promise<T>, ms: number, deps: unknown[]) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    const tick = () =>
      fn()
        .then((d) => alive && (setData(d), setError(null)))
        .catch((e: Error) => alive && setError(e.message));
    tick();
    const t = setInterval(tick, ms);
    return () => {
      alive = false;
      clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, error };
}

function Hub() {
  const inv = usePoll(battles.invitations, 4000, []);
  const mine = usePoll(battles.mine, 4000, []);
  const lb = useLoad(battles.leaderboard);
  const [who, setWho] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const send = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await battles.invite(who.trim(), "subj_python");
      setMsg({ ok: true, text: "Challenge dispatched! They will see it in their Battles arena and notifications." });
      setWho("");
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const respond = async (i: Invitation, accept: boolean) => {
    try {
      const r = await battles.respond(i.id, accept);
      const id = r.battle_id ?? (r as { battle?: { id: string } }).battle?.id;
      if (accept && id) navigate("battles", id);
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  };

  const incoming = (inv.data ?? []).filter((i) => i.status === "PENDING");

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">MULTIPLAYER ARENA // 1v1 DUELS</div>
          <h1>ENTER THE ARENA</h1>
          <p className="muted">
            Challenge another PragyaX student to the same five questions in real-time.
            Scoring is verified on the server; XP is awarded once per completed match.
          </p>
        </div>
      </header>

      <div className="grid-2">
        <Card>
          <div className="row-between" style={{ marginBottom: 12 }}>
            <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
              <Swords size={20} style={{ color: "var(--color-amber)" }} aria-hidden /> CHALLENGE A PEER
            </h2>
            <Badge variant="accent">PYTHON TRACK</Badge>
          </div>
          <p className="muted small">
            Enter a registered student's email to issue a direct 1v1 battle invitation.
          </p>
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              if (who.trim()) send();
            }}
            style={{ marginTop: 12 }}
          >
            <label className="field" style={{ flex: 1, margin: 0 }}>
              <span>Target Student Email</span>
              <input
                type="email"
                value={who}
                onChange={(e) => setWho(e.target.value)}
                placeholder="peer@college.edu"
                required
              />
            </label>
            <Button type="submit" variant="primary" loading={busy} disabled={!who.trim()}>
              Send Challenge
            </Button>
          </form>
          {msg && (
            <div style={{ marginTop: 12 }}>
              <p className={msg.ok ? "pill-ok" : "pill-bad"} role="status" style={{ padding: "6px 12px", borderRadius: 2 }}>
                {msg.text}
              </p>
            </div>
          )}
          <p className="sticky-note">
            Battles test Python fundamentals (LEGB scope, mutability, comprehensions). Your opponent must have a PragyaX account.
          </p>
        </Card>

        <Card>
          <div className="row-between" style={{ marginBottom: 12 }}>
            <h2 style={{ margin: 0 }}>PENDING INVITATIONS</h2>
            <span className="badge badge-primary">{incoming.length} PENDING</span>
          </div>
          {inv.error && <ErrorBox message={inv.error} />}
          {incoming.length === 0 && (
            <Empty title="No incoming battle challenges">
              <p className="muted small">When peers challenge you, their duels appear here ready for acceptance.</p>
            </Empty>
          )}
          {incoming.map((i) => (
            <div
              key={i.id}
              className="row-between"
              style={{
                padding: "12px 14px",
                border: "2px solid var(--border-strong)",
                boxShadow: "var(--shadow-sm)",
                borderRadius: "var(--radius-xs)",
                marginBottom: 8,
                backgroundColor: "var(--color-white)",
              }}
            >
              <div>
                <strong>{i.sender_name}</strong>
                <p className="muted small" style={{ margin: 0 }}>Challenged you to a Python Duel</p>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <Button size="sm" variant="primary" leftIcon={Check} onClick={() => respond(i, true)}>
                  Accept & Enter
                </Button>
                <Button size="sm" variant="ghost" leftIcon={X} onClick={() => respond(i, false)}>
                  Decline
                </Button>
              </div>
            </div>
          ))}
        </Card>
      </div>

      <section style={{ marginTop: 16 }}>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>YOUR BATTLE HISTORY</h2>
          <span className="badge">{(mine.data ?? []).length} MATCHES</span>
        </div>
        {mine.data && mine.data.length === 0 && (
          <Empty title="No recorded arena battles yet">
            <p className="muted">Send a challenge above or accept an incoming duel to play your first match.</p>
          </Empty>
        )}
        <div className="chat-grid">
          {(mine.data ?? []).map((b) => (
            <button
              key={b.id}
              className="card chat-tile"
              onClick={() => navigate("battles", b.id)}
              aria-label={`Open battle vs ${b.opponent_name}`}
            >
              <div className="row-between">
                <strong style={{ fontSize: "1.05rem" }}>VS {b.opponent_name.toUpperCase()}</strong>
                <Badge
                  variant={
                    b.status === "COMPLETED"
                      ? b.you_won
                        ? "success"
                        : b.outcome === "TIE"
                        ? "default"
                        : "error"
                      : "accent"
                  }
                >
                  {b.status === "COMPLETED"
                    ? b.outcome === "TIE"
                      ? "TIE MATCH"
                      : b.you_won
                      ? "VICTORY 🏆"
                      : "DEFEAT"
                    : b.status.toUpperCase()}
                </Badge>
              </div>
              <span className="muted small">Match created {formatDate(b.created_at)}</span>
            </button>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>ARENA LEADERBOARD // DUEL STANDINGS</h2>
          <span className="badge badge-accent">OFFICIAL SERVER RANKING</span>
        </div>
        {lb.data && lb.data.length === 0 ? (
          <Empty title="No completed battles recorded on the server yet" />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th style={{ width: 60 }}>Rank</th>
                  <th>Student Gladiator</th>
                  <th style={{ width: 100 }}>Wins</th>
                  <th style={{ width: 100 }}>Losses</th>
                  <th style={{ width: 100 }}>Ties</th>
                </tr>
              </thead>
              <tbody>
                {(lb.data ?? []).map((r, i) => (
                  <tr key={r.user_id}>
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
                    <td><strong>{r.name}</strong></td>
                    <td><span className="pill-ok" style={{ fontWeight: 800 }}>{r.wins}W</span></td>
                    <td><span className="pill-bad" style={{ fontWeight: 800 }}>{r.losses}L</span></td>
                    <td><span className="badge">{r.ties}T</span></td>
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

function Arena({ id }: { id: string }) {
  const { data: v, error } = usePoll<BattleView>(() => battles.view(id), 2500, [id]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [left, setLeft] = useState<number | null>(null);
  const started = useRef<number>(Date.now());
  const autoSent = useRef(false);

  const status = v?.status;
  const total = v?.questions.length ?? 0;

  // Countdown from the server's time limit
  useEffect(() => {
    if (status !== "ACTIVE" || !v || v.viewer_submitted) return;
    started.current = Date.now();
    const t = setInterval(
      () =>
        setLeft(
          Math.max(
            0,
            v.time_limit_seconds * Math.max(total, 1) -
              Math.floor((Date.now() - started.current) / 1000)
          )
        ),
      500
    );
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, v?.viewer_submitted]);

  const submit = async () => {
    setBusy(true);
    setErr(null);
    try {
      await battles.submit(id, answers, Math.round((Date.now() - started.current) / 1000));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (left === 0 && !autoSent.current && !v?.viewer_submitted) {
      autoSent.current = true;
      submit();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left]);

  if (error && !v)
    return (
      <div className="page narrow">
        <ErrorBox message={error} />
        <Button onClick={() => navigate("battles")}>Back to Battles</Button>
      </div>
    );
  if (!v) return <Loading label="Connecting to Battle Arena…" />;

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <div className="eyebrow">ARENA DUEL // LIVE SYNCHRONIZATION</div>
          <h1>VS {v.opponent_display_name.toUpperCase()}</h1>
          <p className="muted">Status: <strong style={{ color: "var(--text-primary)" }}>{v.status}</strong></p>
        </div>
        <Button variant="ghost" onClick={() => navigate("battles")}>
          ← Exit to Hub
        </Button>
      </header>

      {/* State 1: Lobby / Waiting for ready */}
      {v.status === "CREATED" && (
        <Card className="lobby" style={{ textAlign: "center", padding: "40px 24px" }}>
          <div className="row-between" style={{ justifyContent: "center", gap: 32, marginBottom: 20 }}>
            <div
              style={{
                border: "2px solid var(--border-strong)",
                padding: "16px 28px",
                background: "var(--brand-gradient)",
                color: "#FFFFFF",
                boxShadow: "var(--shadow-md)",
                borderRadius: "var(--radius-xs)",
              }}
            >
              <strong style={{ fontSize: "1.2rem", color: "#FFFFFF" }}>YOU</strong>
            </div>
            <div className="vs">VS</div>
            <div
              style={{
                border: "2px solid var(--border-strong)",
                padding: "16px 28px",
                background: "var(--color-purple)",
                color: "#FFFFFF",
                boxShadow: "var(--shadow-md)",
                borderRadius: "var(--radius-xs)",
              }}
            >
              <strong style={{ fontSize: "1.2rem" }}>{v.opponent_display_name.toUpperCase()}</strong>
            </div>
          </div>
          <p className="muted" style={{ maxWidth: 440, margin: "0 auto 20px" }}>
            Both gladiator students must mark ready. The 5-question code duel initiates automatically once confirmed.
          </p>
          <div style={{ display: "inline-block" }}>
            <Button
              variant="primary"
              size="lg"
              loading={busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await battles.ready(id);
                } catch (e) {
                  setErr((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              I Am Ready
            </Button>
          </div>
          {err && <ErrorBox message={err} />}
          <div style={{ marginTop: 24, display: "flex", justifyContent: "center" }}>
            <span className="sticky-note">
              <RefreshCw size={13} className="spin" aria-hidden /> Synchronizing match state with server…
            </span>
          </div>
        </Card>
      )}

      {/* State 2: Active Battle */}
      {v.status === "ACTIVE" && !v.viewer_submitted && (
        <>
          <div className="row-between" style={{ marginBottom: 12 }}>
            <span className="badge badge-primary">
              {Object.keys(answers).length}/{total} QUESTIONS ANSWERED
            </span>
            {left !== null && (
              <span className={`timer ${left < 20 ? "low" : ""}`} role="timer" aria-live="off">
                ⏱ {Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")}
              </span>
            )}
          </div>

          {v.questions.map((q) => (
            <section key={q.question_id} className="card question" style={{ margin: "14px 0" }}>
              <div className="row-between">
                <span className="muted small">Question {q.position} of {total}</span>
                <span className="badge">{q.topic}</span>
              </div>
              <pre className="question-text">{q.question_text}</pre>
              <fieldset className="options">
                <legend className="sr-only">Choose one answer</legend>
                {(["A", "B", "C", "D"] as const).map((k) => (
                  <label key={k} className={`option ${answers[q.question_id] === k ? "chosen" : ""}`}>
                    <input
                      type="radio"
                      name={q.question_id}
                      checked={answers[q.question_id] === k}
                      onChange={() => setAnswers({ ...answers, [q.question_id]: k })}
                    />
                    <span className="option-key">{k}</span>
                    <span>{q[`option_${k.toLowerCase()}` as "option_a"]}</span>
                  </label>
                ))}
              </fieldset>
            </section>
          ))}
          {err && <ErrorBox message={err} />}
          <div style={{ marginTop: 16 }}>
            <Button
              variant="primary"
              size="lg"
              block
              loading={busy}
              onClick={submit}
            >
              Submit Duel Answers
            </Button>
          </div>
          <p className="sticky-note">
            Fast submissions earn time advantages on ties. Unanswered questions are scored as incorrect.
          </p>
        </>
      )}

      {/* State 3: Submitted, waiting for opponent */}
      {v.status === "ACTIVE" && v.viewer_submitted && (
        <Card className="lobby" style={{ textAlign: "center", padding: "48px 24px" }}>
          <h2 style={{ fontFamily: "var(--font-display)", fontSize: "2.4rem" }}>ANSWERS LOCKED IN 🔒</h2>
          <p className="muted">
            Your submissions are safely recorded on the server. Awaiting {v.opponent_display_name} to finish their timer…
          </p>
          <div style={{ marginTop: 20, display: "inline-flex" }}>
            <span className="sticky-note">
              <RefreshCw size={14} className="spin" aria-hidden /> Awaiting opponent final submission…
            </span>
          </div>
        </Card>
      )}

      {/* State 4: Battle Completed */}
      {v.status === "COMPLETED" && v.result && (
        <>
          <div
            className={`callout ${
              v.result.outcome === "TIE"
                ? ""
                : v.result.winner_user_id === v.viewer_user_id
                ? ""
                : "callout-limit"
            }`}
            style={{
              padding: 24,
              border: "3px solid var(--border-strong)",
              boxShadow: "var(--shadow-lg)",
            }}
            role="status"
          >
            <div>
              <strong style={{ fontSize: "1.4rem", fontFamily: "var(--font-display)", letterSpacing: "0.02em" }}>
                {v.result.outcome === "TIE"
                  ? "MATCH OUTCOME: TIED DUEL"
                  : v.result.winner_user_id === v.viewer_user_id
                  ? "VICTORY SECURED! 🏆"
                  : `${v.opponent_display_name.toUpperCase()} PREVAILED`}
              </strong>
              <p style={{ margin: "8px 0" }}>
                {v.result.scores
                  .map((s) => `${s.user_id === v.viewer_user_id ? "You" : v.opponent_display_name}: ${s.correct}/${s.total}`)
                  .join(" · ")}
                . Verified on server; XP ledger updated.
              </p>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 8 }}>
              <Button
                variant="accent"
                onClick={async () => {
                  try {
                    await battles.rematch(id);
                    navigate("battles");
                  } catch (e) {
                    setErr((e as Error).message);
                  }
                }}
              >
                Offer Rematch
              </Button>
              <Button variant="outline" onClick={() => navigate("profile")}>
                View Skill Profile
              </Button>
            </div>
          </div>

          {err && <ErrorBox message={err} />}

          <h2 style={{ marginTop: 24 }}>POST-MATCH QUESTION REVIEW</h2>
          {v.review.map((r) => (
            <Card key={r.question_id} className="question" style={{ marginBottom: 14 }}>
              <strong>
                Q{r.position}. {v.questions.find((q) => q.question_id === r.question_id)?.question_text}
              </strong>
              <div style={{ margin: "10px 0" }}>
                <p>
                  Correct Answer: <strong style={{ color: "var(--color-success)" }}>{r.correct_option}</strong> ·
                  Your Answer: <strong>{r.answers[v.viewer_user_id] ?? "—"}</strong>
                </p>
              </div>
              <p className="muted small">{r.explanation}</p>
            </Card>
          ))}
        </>
      )}
    </div>
  );
}

export default function BattlesPage({ battleId }: { battleId?: string }) {
  return battleId ? <Arena id={battleId} /> : <Hub />;
}
