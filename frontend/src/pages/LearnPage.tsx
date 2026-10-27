import { useEffect, useRef, useState, type FormEvent } from "react";
import { Archive, ArrowRight, Bot, ClipboardCheck, Lock, Pencil, Plus, Send, Sparkles, User as UserIcon } from "lucide-react";
import { learn, type ChatState, type ChatSummary, type DiagQuestion, type Msg } from "../api/learn";
import Markdown from "../components/Markdown";
import { Badge, Button, Card, ProgressBar } from "../components/ui";
import { DemoBadge, Empty, ErrorBox, Loading, formatDate, levelClass } from "../components/States";
import { navigate, useLoad } from "../hooks";

const MODES: { id: string; label: string }[] = [
  { id: "explain", label: "Explain" }, { id: "hint", label: "Hint only" }, { id: "simpler", label: "Simpler" },
  { id: "socratic", label: "Socratic" }, { id: "mistake", label: "Why was I wrong?" }, { id: "hinglish", label: "Hinglish" },
];
const SUBJECT_BLURB: Record<string, string> = {
  subj_python: "Programming, debugging and mini-projects",
  subj_biology: "Cells, genetics, photosynthesis and enzymes",
  subj_business: "Accounting, pricing, unit economics, strategy",
  subj_aiml: "ML paradigms, metrics, optimisation, neural nets",
};

/* ------------------------------------------------------------------ hub */
function ChatHub() {
  const [showArchived,setShowArchived]=useState(false);
  const { data, error, loading, reload } = useLoad(() => learn.chats(showArchived),[showArchived]);
  const catalog = useLoad(learn.catalog);
  const [custom, setCustom] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const create = async (body: { subject_id?: string; custom_subject?: string }, key: string) => {
    setBusy(key);
    setErr(null);
    try {
      const chat = await learn.createChat(body);
      navigate("learn", chat.id);
    } catch (e) {
      setErr((e as Error).message);
      setBusy(null);
    }
  };

  if (loading || catalog.loading) return <Loading label="Loading your learning chats…" />;
  if (error || catalog.error || !data || !catalog.data) return <ErrorBox message={error ?? catalog.error ?? "Catalog unavailable"} onRetry={()=>{reload();catalog.reload();}} />;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>My Learning Chats</h1>
          <p className="muted">Each chat is its own space for one subject: its own mentor conversation, diagnostic, roadmap and progress. Nothing is mixed between chats.</p>
        </div>
      </header>

      <label className="option"><input type="checkbox" checked={showArchived} onChange={e=>setShowArchived(e.target.checked)}/> Include archived chats</label>
      {data.chats.length > 0 && (
        <section aria-label="Your chats" style={{ marginBottom: 28 }}>
          <div className="chat-grid">
            {data.chats.map((c) => <ChatTile key={c.id} chat={c} />)}
          </div>
        </section>
      )}
      {data.chats.length === 0 && (
        <Empty title="Start your first learning chat">
          <p className="muted">Pick a subject below. You'll take a short 5-question diagnostic and get a personalised roadmap.</p>
        </Empty>
      )}

      <section aria-label="New chat">
        <h2><Plus size={18} aria-hidden /> New learning chat</h2>
        {err && <ErrorBox message={err} />}
        <div className="chat-grid">
          {(catalog.data?.subjects ?? []).map((s) => (
            <Card key={s.id} className="chat-tile">
              <h3>{s.title}</h3>
              <p className="muted small">{SUBJECT_BLURB[s.id]} · {s.modules} modules</p>
              <Badge variant="success">Curated curriculum</Badge>
              <Button loading={busy === s.id} onClick={() => create({ subject_id: s.id }, s.id)} rightIcon={ArrowRight}>Start chat</Button>
            </Card>
          ))}
          <Card className="chat-tile">
            <h3>Any other subject</h3>
            <p className="muted small">Physics, History, Economics… The mentor answers through the configured AI provider. There is no validated curriculum, diagnostic or roadmap for these.</p>
            <Badge variant="warning">Mentor only</Badge>
            <form className="inline-form" onSubmit={(e) => { e.preventDefault(); if (custom.trim().length > 1) create({ custom_subject: custom.trim() }, "custom"); }}>
              <label className="sr-only" htmlFor="custom-subject">Subject name</label>
              <input id="custom-subject" value={custom} onChange={(e) => setCustom(e.target.value)} placeholder="e.g. World History" maxLength={80} />
              <Button type="submit" variant="outline" loading={busy === "custom"} disabled={custom.trim().length < 2}>Create</Button>
            </form>
          </Card>
        </div>
      </section>
    </div>
  );
}

function ChatTile({ chat }: { chat: ChatSummary }) {
  return (
    <button className="card chat-tile" onClick={() => navigate("learn", chat.id)} aria-label={`Open ${chat.title}`}>
      <div className="row-between">
        <h3>{chat.title} {chat.status === "archived" && <Badge>Archived</Badge>}</h3>
        {chat.curated ? <Badge variant="primary">{chat.subject_title}</Badge> : <Badge variant="warning">Mentor only</Badge>}
      </div>
      {chat.curated ? (
        chat.has_diagnostic ? (
          <>
            <ProgressBar value={chat.overall_progress} label={`${chat.modules_completed}/${chat.modules_total} modules`} />
            <span className="muted small">Next: {chat.current_module_title ?? "reassess your level"}</span>
          </>
        ) : <span className="muted small">Diagnostic not taken yet</span>
      ) : <span className="muted small">Open-ended mentor conversation</span>}
      {chat.latest_score && <span className={levelClass(chat.latest_score.level)}>{chat.latest_score.level} · {chat.latest_score.percentage}%</span>}
      <span className="muted small">Updated {formatDate(chat.updated_at)}</span>
    </button>
  );
}

/* ------------------------------------------------------------------ workspace */
type Tab = "mentor" | "roadmap" | "revision" | "progress";

function Workspace({ chatId }: { chatId: string }) {
  const { data, error, loading, reload, setData } = useLoad(() => learn.chat(chatId), [chatId]);
  const [tab, setTab] = useState<Tab>("mentor");
  const [showDiag, setShowDiag] = useState(false);
  const [renaming, setRenaming] = useState(false);
  const [title, setTitle] = useState("");

  if (loading) return <Loading label="Opening your chat…" />;
  if (error || !data) return <ErrorBox message={error ?? "Chat not found"} onRetry={reload} />;
  const c = data;
  const needsDiag = c.curated && !c.has_diagnostic;

  const act = (a: ChatState["next_recommendation"]) => {
    if (a.action === "module" && a.module_id) navigate("module", c.id, a.module_id);
    else if (a.action === "diagnostic" || a.action === "reassess") setShowDiag(true);
    else if (a.action === "revision") setTab("revision");
    else setTab("mentor");
  };

  const saveTitle = async () => {
    if (title.trim()) setData(await learn.patchChat(c.id, { title: title.trim() }));
    setRenaming(false);
  };
  const archive = async () => {
    await learn.patchChat(c.id, { archived: c.status === "active" });
    if (c.status === "active") navigate("learn"); else reload();
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          {renaming ? (
            <form className="inline-form" onSubmit={(e) => { e.preventDefault(); saveTitle(); }}>
              <input aria-label="Chat title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={80} autoFocus />
              <Button type="submit" size="sm">Save</Button>
              <Button type="button" size="sm" variant="ghost" onClick={() => setRenaming(false)}>Cancel</Button>
            </form>
          ) : (
            <h1>{c.title}</h1>
          )}
          <p className="muted">
            {c.subject_title} {c.latest_score && <span className={levelClass(c.latest_score.level)}>{c.latest_score.level}</span>}
            {c.status === "archived" && <Badge variant="soon">Archived</Badge>}
          </p>
        </div>
        <div className="actions">
          <Button variant="ghost" size="sm" leftIcon={Pencil} onClick={() => { setTitle(c.title); setRenaming(true); }}>Rename</Button>
          <Button variant="ghost" size="sm" leftIcon={Archive} onClick={archive}>{c.status === "active" ? "Archive" : "Restore"}</Button>
          <Button variant="ghost" size="sm" onClick={() => navigate("learn")}>All chats</Button>
        </div>
      </header>

      {c.limitation && <div className="callout callout-limit" role="note"><div><strong>Limited mode</strong>{c.limitation}</div></div>}

      {c.curated && (
        <div className="callout">
          <div><strong>Next step</strong>{c.next_recommendation.text}</div>
          <Button variant="accent" rightIcon={ArrowRight} onClick={() => act(c.next_recommendation)}>
            {c.next_recommendation.action === "diagnostic" ? "Start diagnostic" : c.next_recommendation.action === "module" ? "Open lesson"
              : c.next_recommendation.action === "revision" ? "Review mistakes" : c.next_recommendation.action === "reassess" ? "Reassess" : "Ask mentor"}
          </Button>
        </div>
      )}

      {(needsDiag || showDiag) && c.status === "active" ? (
        <Diagnostic chatId={c.id} isRetake={c.has_diagnostic} onDone={() => { setShowDiag(false); reload(); setTab(c.has_diagnostic ? "progress" : "roadmap"); }} onCancel={needsDiag ? undefined : () => setShowDiag(false)} />
      ) : (
        <>
          <div className="tabs-row" role="tablist">
            {([["mentor", "AI Mentor"], ["roadmap", "Roadmap"], ["revision", `Revision${c.unresolved_mistakes ? ` (${c.unresolved_mistakes})` : ""}`], ["progress", "Progress"]] as [Tab, string][])
              .filter(([id]) => c.curated || id === "mentor")
              .map(([id, label]) => (
                <button key={id} role="tab" aria-selected={tab === id} className={`tab ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>{label}</button>
              ))}
          </div>
          {tab === "mentor" && <Mentor chat={c} />}
          {tab === "roadmap" && <Roadmap chat={c} />}
          {tab === "revision" && <Revision chatId={c.id} />}
          {tab === "progress" && <Progress chat={c} onReassess={() => setShowDiag(true)} />}
        </>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ diagnostic */
function Diagnostic({ chatId, isRetake, onDone, onCancel }: { chatId: string; isRetake: boolean; onDone: () => void; onCancel?: () => void }) {
  const { data, error, loading, reload } = useLoad(() => learn.diagQuestions(chatId), [chatId]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<Awaited<ReturnType<typeof learn.submitDiag>> | null>(null);

  if (loading) return <Loading label="Loading questions…" />;
  if (error || !data) return <ErrorBox message={error ?? "No questions"} onRetry={reload} />;
  const qs: DiagQuestion[] = data.questions;
  const opt = (q: DiagQuestion, k: string) => ({ A: q.option_a, B: q.option_b, C: q.option_c, D: q.option_d }[k] ?? "");

  if (result) {
    return (
      <Card className="question">
        <h2><ClipboardCheck size={20} aria-hidden /> {result.kind === "reassessment" ? "Reassessment" : "Diagnostic"} result: {result.score}/{result.total}</h2>
        <p><span className={levelClass(result.proficiency_level)}>{result.proficiency_level}</span> · {result.percentage}% {result.is_mock && <DemoBadge label="Mock feedback" />}</p>
        <p className="muted">{result.summary_feedback}</p>
        <p className="sticky-note">This is a short 5-question indication of your level, not an accredited assessment. Scores are graded on the server from fixed answer keys.</p>
        <Button onClick={onDone} rightIcon={ArrowRight}>{result.kind === "reassessment" ? "See my progress" : "See my roadmap"}</Button>
      </Card>
    );
  }

  const submit = async () => {
    setBusy(true); setErr(null);
    try { setResult(await learn.submitDiag(chatId, answers)); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  const done = qs.filter((q) => answers[q.id]).length;

  return (
    <div>
      <h2>{isRetake ? "Reassessment" : "Diagnostic assessment"}</h2>
      <p className="muted">Five focused questions give a limited estimate of your starting point and personalize the roadmap. {isRetake && "Your first score is kept so you can see improvement."}</p>
      {qs.map((q, i) => (
        <section key={q.id} className="card question" style={{ marginBottom: 14 }}>
          <div className="row-between"><span className="muted small">Question {i + 1} of {qs.length} · {q.difficulty}</span><span className="badge">{q.topic}</span></div>
          <pre className="question-text">{q.question_text}</pre>
          <fieldset className="options">
            <legend className="sr-only">Choose one answer</legend>
            {["A", "B", "C", "D"].map((k) => (
              <label key={k} className={`option ${answers[q.id] === k ? "chosen" : ""}`}>
                <input type="radio" name={q.id} checked={answers[q.id] === k} onChange={() => setAnswers({ ...answers, [q.id]: k })} />
                <span className="option-key">{k}</span><span>{opt(q, k)}</span>
              </label>
            ))}
          </fieldset>
        </section>
      ))}
      {err && <ErrorBox message={err} />}
      <div className="actions">
        <Button loading={busy} disabled={done < qs.length} onClick={submit} leftIcon={Send}>{done < qs.length ? `Answer all ${qs.length} (${done} done)` : "Submit for grading"}</Button>
        {onCancel && <Button variant="ghost" onClick={onCancel}>Cancel</Button>}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ mentor */
function Mentor({ chat }: { chat: ChatState }) {
  const { data, error, loading, reload, setData } = useLoad(() => learn.messages(chat.id), [chat.id]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState("explain");
  const [sending, setSending] = useState(false);
  const [sendErr, setSendErr] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const messages = data?.messages ?? [];
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length, sending]);

  if (loading) return <Loading label="Loading conversation…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;
  const archived = chat.status !== "active";

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || sending) return;
    setSending(true); setSendErr(null); setInput("");
    const local: Msg = { id: `local-${Date.now()}`, role: "user", content: message, suggested_followups: [] };
    setData({ messages: [...messages, local] });
    try {
      const reply = await learn.send(chat.id, message, mode);
      setData((d) => (d ? { messages: [...d.messages, reply] } : d));
    } catch (e) {
      setSendErr((e as Error).message); setInput(message);
      setData((d) => (d ? { messages: d.messages.filter((m) => m.id !== local.id) } : d));
    } finally { setSending(false); }
  };
  const last = [...messages].reverse().find((m) => m.role === "assistant");
  const starters = [`Explain the basics of ${chat.subject_title}`, chat.current_module?.title ? `Help me understand: ${chat.current_module.title}` : "What should I learn first?"];

  return (
    <section className="card chat">
      <div className="chat-log" aria-live="polite">
        {messages.length === 0 && <Empty title="Ask your first question"><p className="muted">The mentor knows this chat's subject{chat.weaknesses.length ? " and your weak topics" : ""}.</p></Empty>}
        {messages.map((m) => (
          <div key={m.id} className={`msg msg-${m.role}`}>
            <div className="msg-avatar" aria-hidden>{m.role === "user" ? <UserIcon size={16} /> : <Bot size={16} />}</div>
            <div className="msg-bubble">
              <span className="sr-only">{m.role === "user" ? "You said:" : "Mentor said:"}</span>
              {m.role === "assistant" ? <Markdown text={m.content} /> : <p>{m.content}</p>}
              {m.notice && <p className="sticky-note"><Sparkles size={12} aria-hidden /> {m.notice}</p>}
              {m.role === "assistant" && m.is_mock && <DemoBadge />}
            </div>
          </div>
        ))}
        {sending && <div className="msg msg-assistant"><div className="msg-avatar" aria-hidden><Bot size={16} /></div><div className="msg-bubble typing" aria-label="Mentor is typing"><span /><span /><span /></div></div>}
        <div ref={endRef} />
      </div>
      <div className="chips" role="group" aria-label="Mentor style">
        {MODES.map((m) => <button key={m.id} className={`chip ${mode === m.id ? "chosen" : ""}`} aria-pressed={mode === m.id} onClick={() => setMode(m.id)}>{m.label}</button>)}
      </div>
      <div className="chips">
        {(last?.suggested_followups.length ? last.suggested_followups : starters).map((s) => <button key={s} className="chip" onClick={() => send(s)} disabled={sending || archived}>{s}</button>)}
      </div>
      {sendErr && <ErrorBox message={sendErr} />}
      {archived ? <p className="muted">This chat is archived. Restore it to continue.</p> : (
        <form className="chat-input" onSubmit={(e: FormEvent) => { e.preventDefault(); send(input); }}>
          <label htmlFor="mentor-msg" className="sr-only">Your question</label>
          <input id="mentor-msg" value={input} onChange={(e) => setInput(e.target.value)} placeholder={mode === "hint" ? "Paste the problem; I'll nudge, not solve" : "Ask anything about this subject"} maxLength={2000} autoComplete="off" />
          <button className="btn btn-primary" disabled={sending || !input.trim()} aria-label="Send message"><Send size={16} aria-hidden /></button>
        </form>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ roadmap */
function Roadmap({ chat }: { chat: ChatState }) {
  if (!chat.roadmap) return <Empty title="No roadmap yet"><p className="muted">Take the diagnostic to generate it.</p></Empty>;
  return (
    <div className="split">
      <section>
        <ProgressBar value={chat.overall_progress} label={`${chat.modules_completed} of ${chat.modules_total} modules complete`} />
        <ol className="road" style={{ marginTop: 14 }}>
          {chat.roadmap.modules.map((m, i) => (
            <li key={m.id} className={`road-item ${m.status}`}>
              <span className="road-dot" aria-hidden>{m.status === "locked" ? <Lock size={14} /> : i + 1}</span>
              <div>
                <div className="road-title">{m.title}</div>
                <div className="muted small">{m.difficulty} · ~{m.estimated_minutes} min{m.mastery_percentage != null ? ` · mastery ${m.mastery_percentage}%` : ""}</div>
              </div>
              {m.status === "locked"
                ? <Badge variant="soon">Locked</Badge>
                : <Button size="sm" variant={m.status === "completed" ? "outline" : "accent"} onClick={() => navigate("module", chat.id, m.id)}>{m.status === "completed" ? "Review" : "Study"}</Button>}
            </li>
          ))}
        </ol>
      </section>
      <aside className="card">
        <h3>Why this path?</h3>
        <p className="muted small">{chat.roadmap.description}</p>
        {chat.weaknesses.length > 0 && <><strong className="small">Focus areas</strong><ul className="small">{chat.weaknesses.map((w) => <li key={w}>{w}</li>)}</ul></>}
        {chat.strengths.length > 0 && <><strong className="small">Strengths</strong><ul className="small">{chat.strengths.map((w) => <li key={w}>{w}</li>)}</ul></>}
        <p className="sticky-note">{chat.level_note}</p>
      </aside>
    </div>
  );
}

/* ------------------------------------------------------------------ revision */
function Revision({ chatId }: { chatId: string }) {
  const { data, error, loading, reload } = useLoad(() => learn.revision(chatId), [chatId]);
  if (loading) return <Loading label="Loading revision list…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;
  return (
    <div>
      <p className="muted">{data.suggestion}</p>
      {data.priorities.length > 0 && <div className="chips">{data.priorities.map((p) => <Badge key={p.module_title} variant="warning">{p.module_title}: {p.missed} missed</Badge>)}</div>}
      {data.items.length === 0 && <Empty title="Nothing to revise" />}
      {data.items.map((it, i) => (
        <Card key={i} className="question" >
          <div className="row-between"><strong>{it.question}</strong><Badge>{it.module_title}</Badge></div>
          <div className="fb wrong">Your answer: {it.your_answer}</div>
          <div className="fb right">Correct: {it.correct_answer}<br /><span className="muted">{it.explanation}</span></div>
        </Card>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ progress */
function Progress({ chat, onReassess }: { chat: ChatState; onReassess: () => void }) {
  return (
    <div className="grid-2">
      <Card>
        <h3>Measured improvement</h3>
        {chat.improvement ? (
          <p><strong>{chat.improvement.first_percentage}% → {chat.improvement.latest_percentage}%</strong> ({chat.improvement.delta >= 0 ? "+" : ""}{chat.improvement.delta} points)</p>
        ) : <p className="muted">Retake the assessment after studying to see your before/after.</p>}
        <p className="sticky-note">Reassessments reuse this subject's diagnostic bank, so a high retake score can partly reflect memory. Practice mastery below is the stronger signal.</p>
        <Button onClick={onReassess} variant="outline">Retake assessment</Button>
      </Card>
      <Card>
        <h3>Score history</h3>
        {chat.assessment_history.length === 0 && <p className="muted">No attempts yet.</p>}
        <table className="table"><tbody>
          {chat.assessment_history.map((a) => (
            <tr key={a.id}><td>{a.kind}</td><td>{a.score}/{a.total} ({a.percentage}%)</td><td>{formatDate(a.created_at)}</td></tr>
          ))}
        </tbody></table>
      </Card>
    </div>
  );
}

export default function LearnPage({ chatId }: { chatId?: string }) {
  return chatId ? <Workspace chatId={chatId} /> : <ChatHub />;
}
