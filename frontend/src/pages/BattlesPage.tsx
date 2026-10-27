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
    const tick = () => fn().then((d) => alive && (setData(d), setError(null))).catch((e: Error) => alive && setError(e.message));
    tick();
    const t = setInterval(tick, ms);
    return () => { alive = false; clearInterval(t); };
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
    setBusy(true); setMsg(null);
    try {
      await battles.invite(who.trim(), "subj_python");
      setMsg({ ok: true, text: "Invitation sent. They'll see it in their Battles page and notifications." }); setWho("");
    } catch (e) { setMsg({ ok: false, text: (e as Error).message }); } finally { setBusy(false); }
  };
  const respond = async (i: Invitation, accept: boolean) => {
    try {
      const r = await battles.respond(i.id, accept);
      const id = r.battle_id ?? (r as { battle?: { id: string } }).battle?.id;
      if (accept && id) navigate("battles", id);
    } catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
  };

  const incoming = (inv.data ?? []).filter((i) => i.status === "PENDING");
  return (
    <div className="page">
      <header className="page-head">
        <div><h1>1v1 Battles</h1><p className="muted">Challenge another PragyaX student to the same five questions. Scoring is done on the server; XP is awarded once.</p></div>
      </header>

      <div className="grid-2">
        <Card>
          <h2><Swords size={18} aria-hidden /> Challenge a student</h2>
          <form className="inline-form" onSubmit={(e) => { e.preventDefault(); if (who.trim()) send(); }}>
            <label className="field" style={{ flex: 1 }}>Their PragyaX email
              <input type="email" value={who} onChange={(e) => setWho(e.target.value)} placeholder="friend@college.edu" required />
            </label>
            <Button type="submit" loading={busy} disabled={!who.trim()}>Send invitation</Button>
          </form>
          {msg && <p className={msg.ok ? "pill-ok" : "pill-bad"} role="status">{msg.text}</p>}
          <p className="sticky-note">Battles are Python for now. Your opponent must already have an account.</p>
        </Card>
        <Card>
          <h2>Invitations for you</h2>
          {inv.error && <ErrorBox message={inv.error} />}
          {incoming.length === 0 && <p className="muted">No pending invitations.</p>}
          {incoming.map((i) => (
            <div key={i.id} className="row-between" style={{ padding: "8px 0" }}>
              <span><strong>{i.sender_name}</strong> challenged you</span>
              <span className="actions">
                <Button size="sm" leftIcon={Check} onClick={() => respond(i, true)}>Accept</Button>
                <Button size="sm" variant="ghost" leftIcon={X} onClick={() => respond(i, false)}>Decline</Button>
              </span>
            </div>
          ))}
        </Card>
      </div>

      <h2 style={{ marginTop: 28 }}>Your battles</h2>
      {mine.data && mine.data.length === 0 && <Empty title="No battles yet"><p className="muted">Invite a friend above to play your first one.</p></Empty>}
      <div className="chat-grid">
        {(mine.data ?? []).map((b) => (
          <button key={b.id} className="card chat-tile" onClick={() => navigate("battles", b.id)}>
            <div className="row-between"><strong>vs {b.opponent_name}</strong>
              <Badge variant={b.status === "COMPLETED" ? (b.you_won ? "success" : b.outcome === "TIE" ? "default" : "warning") : "accent"}>
                {b.status === "COMPLETED" ? (b.outcome === "TIE" ? "Tie" : b.you_won ? "Won" : "Lost") : b.status.toLowerCase()}
              </Badge></div>
            <span className="muted small">{formatDate(b.created_at)}</span>
          </button>
        ))}
      </div>

      <h2 style={{ marginTop: 28 }}>Battle leaderboard</h2>
      {lb.data && lb.data.length === 0 ? <p className="muted">No completed battles yet.</p> : (
        <table className="table"><thead><tr><th>#</th><th>Student</th><th>W</th><th>L</th><th>T</th></tr></thead>
          <tbody>{(lb.data ?? []).map((r, i) => <tr key={r.user_id}><td>{i + 1}</td><td>{r.name}</td><td>{r.wins}</td><td>{r.losses}</td><td>{r.ties}</td></tr>)}</tbody></table>
      )}
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

  // Countdown from the server's time limit (server remains authoritative on what counts).
  useEffect(() => {
    if (status !== "ACTIVE" || !v || v.viewer_submitted) return;
    started.current = Date.now();
    const t = setInterval(() => setLeft(Math.max(0, v.time_limit_seconds * Math.max(total, 1) - Math.floor((Date.now() - started.current) / 1000))), 500);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, v?.viewer_submitted]);

  const submit = async () => {
    setBusy(true); setErr(null);
    try { await battles.submit(id, answers, Math.round((Date.now() - started.current) / 1000)); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  useEffect(() => {
    if (left === 0 && !autoSent.current && !v?.viewer_submitted) { autoSent.current = true; submit(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [left]);

  if (error && !v) return <div className="page"><ErrorBox message={error} /><Button onClick={() => navigate("battles")}>Back</Button></div>;
  if (!v) return <Loading label="Opening battle…" />;

  return (
    <div className="page narrow">
      <header className="page-head">
        <div><h1>Battle vs {v.opponent_display_name}</h1><p className="muted">Status: {v.status.toLowerCase()}</p></div>
        <Button variant="ghost" onClick={() => navigate("battles")}>All battles</Button>
      </header>

      {v.status === "CREATED" && (
        <Card className="lobby">
          <div className="vs"><span>You</span><Swords aria-hidden /><span>{v.opponent_display_name}</span></div>
          <p className="muted">Both players must mark ready. The battle starts automatically.</p>
          <Button loading={busy} onClick={async () => { setBusy(true); try { await battles.ready(id); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); } }}>I'm ready</Button>
          {err && <ErrorBox message={err} />}
          <span className="sticky-note"><RefreshCw size={12} aria-hidden /> Checking for your opponent every few seconds…</span>
        </Card>
      )}

      {v.status === "ACTIVE" && !v.viewer_submitted && (
        <>
          <div className="row-between"><span className="muted">{Object.keys(answers).length}/{total} answered</span>
            {left !== null && <span className={`timer ${left < 20 ? "low" : ""}`} role="timer" aria-live="off">{Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")}</span>}</div>
          {v.questions.map((q) => (
            <section key={q.question_id} className="card question" style={{ margin: "12px 0" }}>
              <div className="row-between"><span className="muted small">Question {q.position}</span><span className="badge">{q.topic}</span></div>
              <pre className="question-text">{q.question_text}</pre>
              <fieldset className="options"><legend className="sr-only">Choose one answer</legend>
                {(["A", "B", "C", "D"] as const).map((k) => (
                  <label key={k} className={`option ${answers[q.question_id] === k ? "chosen" : ""}`}>
                    <input type="radio" name={q.question_id} checked={answers[q.question_id] === k} onChange={() => setAnswers({ ...answers, [q.question_id]: k })} />
                    <span className="option-key">{k}</span><span>{q[`option_${k.toLowerCase()}` as "option_a"]}</span>
                  </label>
                ))}
              </fieldset>
            </section>
          ))}
          {err && <ErrorBox message={err} />}
          <Button loading={busy} onClick={submit}>Submit answers</Button>
          <p className="sticky-note">You can submit with unanswered questions; they count as wrong.</p>
        </>
      )}

      {v.status === "ACTIVE" && v.viewer_submitted && (
        <Card className="lobby"><h2>Answers locked in</h2><p className="muted">Waiting for {v.opponent_display_name} to finish…</p></Card>
      )}

      {v.status === "COMPLETED" && v.result && (
        <>
          <div className={`callout ${v.result.outcome === "TIE" ? "" : v.result.winner_user_id === v.viewer_user_id ? "" : "callout-limit"}`} role="status">
            <div><strong>{v.result.outcome === "TIE" ? "It's a tie" : v.result.winner_user_id === v.viewer_user_id ? "You won! 🏆" : `${v.opponent_display_name} won`}</strong>
              {v.result.scores.map((s) => `${s.user_id === v.viewer_user_id ? "You" : v.opponent_display_name}: ${s.correct}/${s.total}`).join(" · ")}. XP awarded once on the server.</div>
            <span className="actions">
              <Button variant="accent" onClick={async () => { try { await battles.rematch(id); navigate("battles"); } catch (e) { setErr((e as Error).message); } }}>Offer rematch</Button>
              <Button variant="outline" onClick={() => navigate("profile")}>See achievements</Button>
            </span>
          </div>
          {err && <ErrorBox message={err} />}
          {v.review.map((r) => (
            <Card key={r.question_id} className="question">
              <strong>Q{r.position}. {v.questions.find((q) => q.question_id === r.question_id)?.question_text}</strong>
              <p>Correct answer: <strong>{r.correct_option}</strong> · Yours: {r.answers[v.viewer_user_id] ?? "—"}</p>
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
