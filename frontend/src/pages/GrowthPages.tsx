import { useState } from "react";
import { Award, Copy, Download, Gift, Share2 } from "lucide-react";
import { growth, learn, notifications, type Cert, type Prefs } from "../api/learn";
import { Badge, Button, Card, ProgressBar } from "../components/ui";
import { Empty, ErrorBox, Loading, formatDate, levelClass } from "../components/States";
import { navigate, useLoad } from "../hooks";

/* ------------------------------------------------------------------ Skill profile + certificates */
function CertCard({ c }: { c: Cert }) {
  const [msg, setMsg] = useState<string | null>(null);
  const share = async () => {
    try {
      const s = await growth.share(c.verification_id);
      await navigator.clipboard.writeText(s.share_text);
      setMsg("Share text copied.");
    } catch { setMsg("Copy failed; use the verification link."); }
  };
  return (
    <Card>
      <div className="row-between"><strong>{c.title}</strong><Badge variant="accent">{c.cert_type.replace("_", " ")}</Badge></div>
      <p className="muted small">{c.description}</p>
      <p className="small">Verification ID: <code>{c.verification_id}</code></p>
      <div className="actions">
        <a className="btn btn-outline btn-sm" href={`${import.meta.env.VITE_API_URL ?? ""}/api/certificates/${encodeURIComponent(c.verification_id)}/download`} target="_blank" rel="noopener noreferrer"><Download size={14} aria-hidden/> View / print</a>
        <Button size="sm" variant="ghost" leftIcon={Share2} onClick={share}>Copy share text</Button>
        <Button size="sm" variant="ghost" onClick={() => navigate("verify", c.verification_id)}>Public check</Button>
      </div>
      {msg && <p className="sticky-note" role="status">{msg}</p>}
    </Card>
  );
}

export function ProfilePage() {
  const { data, error, loading, reload } = useLoad(learn.skillProfile);
  if (loading) return <Loading label="Building your skill profile…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;
  const g = data.gamification;
  return (
    <div className="page">
      <header className="page-head"><div><h1>Skill Profile</h1><p className="muted">Evidence of what you have actually studied and achieved on PragyaX.</p></div></header>
      <div className="notice-demo">{data.disclaimer}</div>

      <section className="stats">
        <div className="stat card"><span className="stat-label">XP</span><span className="stat-value">{g.total_xp}</span><span className="muted small">Level {g.level} · {g.title}</span></div>
        <div className="stat card"><span className="stat-label">Learning streak</span><span className="stat-value">{g.streak.current_streak}</span><span className="muted small">best {g.streak.longest_streak}</span></div>
        <div className="stat card"><span className="stat-label">Battles</span><span className="stat-value">{g.battle_stats.wins}W</span><span className="muted small">{g.battle_stats.losses} lost · {g.battle_stats.ties} tied</span></div>
        <div className="stat card"><span className="stat-label">Achievements</span><span className="stat-value">{data.certificates.length}</span><span className="muted small">{data.badges.length} badges</span></div>
      </section>

      <h2 style={{ marginTop: 26 }}>Subjects studied</h2>
      {data.subjects.length === 0 && <Empty title="No subjects yet"><Button onClick={() => navigate("learn")}>Start a learning chat</Button></Empty>}
      <div className="chat-grid">
        {data.subjects.map((s) => (
          <button key={s.chat_id} className="card chat-tile" onClick={() => navigate("learn", s.chat_id)}>
            <div className="row-between"><h3>{s.subject_title}</h3>{s.level && <span className={levelClass(s.level)}>{s.level}</span>}</div>
            {s.curated ? <ProgressBar value={s.modules_total ? (100 * s.modules_completed) / s.modules_total : 0} label={`${s.modules_completed}/${s.modules_total} modules`} /> : <span className="muted small">Mentor-only subject</span>}
            {s.improvement && <span className={s.improvement.delta >= 0 ? "pill-ok small" : "pill-bad small"}>{s.improvement.delta >= 0 ? "+" : ""}{s.improvement.delta} pts since first diagnostic</span>}
            {s.mastered_topics.length > 0 && <span className="small">Mastered: {s.mastered_topics.map((m) => m.title).join(", ")}</span>}
            {s.weaknesses.length > 0 && <span className="muted small">Working on: {s.weaknesses.slice(0, 3).join(", ")}</span>}
          </button>
        ))}
      </div>

      <h2 style={{ marginTop: 26 }}>Projects</h2>
      {data.projects.length === 0 ? <p className="muted">No submitted projects. <a className="link" href="#/projects">Browse projects</a></p> : (
        <table className="table"><thead><tr><th>Project</th><th>Level</th><th>Self-rating</th><th>Evidence</th></tr></thead>
          <tbody>{data.projects.map((p) => <tr key={p.id}><td>{p.title}</td><td>{p.level}</td><td>{p.rubric_total}/{p.rubric_max}</td><td><Badge variant="warning">{p.evidence_type}</Badge></td></tr>)}</tbody></table>
      )}

      <h2 style={{ marginTop: 26 }}><Award size={18} aria-hidden /> Achievements & certificates</h2>
      <p className="muted small">"PragyaX Challenge Achievement" records are issued by this platform for specific accomplishments. They are verifiable here but are not accredited qualifications.</p>
      {data.badges.length > 0 && <div className="chips">{data.badges.map((b) => <Badge key={b.badge_key} variant="primary" title={b.description}>{b.title}</Badge>)}</div>}
      {data.certificates.length === 0 && <Empty title="No achievements yet"><p className="muted">Win a battle, finish a learning path or place in a competition.</p></Empty>}
      <div className="grid-2">{data.certificates.map((c) => <CertCard key={c.verification_id} c={c} />)}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ Public verification (no login needed) */
export function VerifyPage({ id }: { id?: string }) {
  const [input, setInput] = useState(id ?? "");
  const { data, error, loading } = useLoad(() => (id ? growth.verify(id) : Promise.resolve(null)), [id]);
  return (
    <div className="page narrow" style={{ margin: "0 auto", padding: 24 }}>
      <a className="brand" href="#/">Pragya<span className="brand-x">X</span></a>
      <h1>Verify an achievement</h1>
      <form className="inline-form" onSubmit={(e) => { e.preventDefault(); if (input.trim()) navigate("verify", input.trim()); }}>
        <label className="field" style={{ flex: 1 }}>Verification ID<input value={input} onChange={(e) => setInput(e.target.value)} placeholder="PRAGYA-CERT-…" /></label>
        <Button type="submit">Check</Button>
      </form>
      {id && loading && <Loading label="Checking signature…" />}
      {id && error && <div className="alert alert-error" role="alert"><strong>Not valid.</strong> {error}</div>}
      {data?.is_valid && (
        <Card>
          <Badge variant="success">Signature verified</Badge>
          <h2>{data.title}</h2>
          <p>Awarded to <strong>{data.recipient_name}</strong></p>
          <p className="muted">{data.description}</p>
          <p className="sticky-note">Issued by PragyaX as a platform achievement record. Not an accredited qualification. {data.issued_at && formatDate(data.issued_at)}</p>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Referrals */
export function ReferralsPage() {
  const { data, error, loading, reload } = useLoad(growth.referrals);
  const [copied, setCopied] = useState(false);
  const [code, setCode] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  if (loading) return <Loading label="Loading referrals…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;
  const copy = async () => { try { await navigator.clipboard.writeText(data.referral_code); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { /* clipboard unavailable */ } };
  const apply = async () => {
    try { const r = await growth.applyReferral(code.trim()); setMsg({ ok: true, text: r.message }); reload(); } catch (e) { setMsg({ ok: false, text: (e as Error).message }); }
  };
  return (
    <div className="page">
      <header className="page-head"><div><h1>Referrals</h1><p className="muted">{data.reward_rule}</p></div></header>
      <div className="grid-2">
        <Card>
          <h2>Your invite code</h2>
          <div className="share-code">{data.referral_code}</div>
          <div className="actions" style={{ marginTop: 10 }}><Button leftIcon={Copy} onClick={copy}>{copied ? "Copied!" : "Copy code"}</Button></div>
          <p className="sticky-note">Friends enter this code when they sign up. A referral is rewarded only after they finish their diagnostic AND their first lesson, so it reflects real learning.</p>
        </Card>
        <Card>
          <h2>Got a friend's code?</h2>
          <p className="muted small">Codes can be applied before you finish your first lesson.</p>
          <div className="inline-form"><label className="sr-only" htmlFor="ref-code">Referral code</label>
            <input id="ref-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="PRAGYA-XXXXXX-0000" />
            <Button onClick={apply} disabled={!code.trim()}>Apply</Button></div>
          {msg && <p className={msg.ok ? "pill-ok" : "pill-bad"} role="status">{msg.text}</p>}
        </Card>
      </div>
      <section className="stats" style={{ marginTop: 20 }}>
        <div className="stat card"><span className="stat-label">Invited</span><span className="stat-value">{data.total_invited}</span></div>
        <div className="stat card"><span className="stat-label">Pending</span><span className="stat-value">{data.pending_referrals}</span></div>
        <div className="stat card"><span className="stat-label">Rewarded</span><span className="stat-value">{data.successful_referrals}</span></div>
        <div className="stat card"><span className="stat-label">XP earned</span><span className="stat-value">{data.xp_earned_from_referrals}</span><span className="muted small">{data.referrer_xp} XP each</span></div>
      </section>
      <h2 style={{ marginTop: 24 }}>People you invited</h2>
      {data.referral_history.length === 0 ? <Empty title="No referrals yet" /> : (
        <table className="table"><thead><tr><th>Student</th><th>Status</th><th>Since</th></tr></thead>
          <tbody>{data.referral_history.map((r) => <tr key={r.id}><td>{r.referee_name}</td><td><Badge variant={r.status === "REWARDED" ? "success" : "warning"}>{r.status}</Badge></td><td>{formatDate(r.created_at)}</td></tr>)}</tbody></table>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Rewards & XP ledger */
export function RewardsPage() {
  const profile = useLoad(growth.profile);
  const ledger = useLoad(growth.ledger);
  const rewards = useLoad(growth.rewards);
  const [msg, setMsg] = useState<string | null>(null);
  if (profile.loading || ledger.loading || rewards.loading) return <Loading label="Loading rewards…" />;
  if (profile.error || !profile.data) return <ErrorBox message={profile.error ?? "No data"} onRetry={profile.reload} />;
  const p = profile.data;
  const redeem = async (id: string) => {
    try { await growth.redeem(id); setMsg("Demo reward redeemed (XP deducted, nothing will be shipped)."); profile.reload(); ledger.reload(); rewards.reload(); }
    catch (e) { setMsg((e as Error).message); }
  };
  return (
    <div className="page">
      <header className="page-head"><div><h1>Rewards & XP</h1><p className="muted">XP is granted by the server for real learning events, once per event.</p></div></header>
      <section className="stats">
        <div className="stat card"><span className="stat-label">Total XP</span><span className="stat-value">{p.total_xp}</span><span className="muted small">Level {p.level} · {p.title}</span></div>
        <div className="stat card"><span className="stat-label">Next level at</span><span className="stat-value">{p.next_threshold}</span><ProgressBar value={p.progress_percentage} label="Level progress" /></div>
      </section>
      <div className="notice-demo"><Gift size={14} aria-hidden /> <strong>Demo rewards.</strong> There is no fulfilment pipeline yet, so nothing below is shipped, scheduled or delivered. Redeeming only demonstrates the XP flow.</div>
      {msg && <p role="status" className="sticky-note">{msg}</p>}
      <div className="chat-grid">
        {(rewards.data ?? []).map((r) => (
          <Card key={r.id} className="chat-tile">
            <div className="row-between"><h3>{r.title}</h3><Badge variant="demo">Demo</Badge></div>
            <p className="muted small">{r.description}</p>
            <Button size="sm" variant="outline" disabled={!r.can_afford} onClick={() => redeem(r.id)}>{r.can_afford ? `Redeem (demo) · ${r.xp_cost} XP` : `${r.shortfall} XP short`}</Button>
          </Card>
        ))}
      </div>
      <h2 style={{ marginTop: 24 }}>XP ledger</h2>
      {(ledger.data ?? []).length === 0 ? <Empty title="No XP yet"><p className="muted">Finish a diagnostic or lesson to earn your first XP.</p></Empty> : (
        <table className="table"><thead><tr><th>When</th><th>Reason</th><th>XP</th></tr></thead>
          <tbody>{(ledger.data ?? []).map((e) => <tr key={e.id}><td>{formatDate(e.created_at)}</td><td>{e.reason}</td><td className={e.points_delta < 0 ? "pill-bad" : "pill-ok"}>{e.points_delta > 0 ? "+" : ""}{e.points_delta}</td></tr>)}</tbody></table>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Notifications */
export function NotificationsPage({ onChange }: { onChange: () => void }) {
  const { data, error, loading, reload } = useLoad(notifications.list);
  const prefs = useLoad(notifications.prefs);
  const [saved, setSaved] = useState<string | null>(null);
  const [draft, setDraft] = useState<Prefs | null>(null);
  if (loading || prefs.loading) return <Loading label="Loading notifications…" />;
  if (error || prefs.error || !data || !prefs.data) return <ErrorBox message={error ?? prefs.error ?? "Preferences unavailable"} onRetry={()=>{reload();prefs.reload();}} />;
  const p = draft ?? prefs.data;
  const markAll = async () => { await notifications.read(); reload(); onChange(); };
  const open = async (n: { id: string; link: string | null; read_at: string | null }) => {
    if (!n.read_at) { await notifications.read(n.id); onChange(); }
    if (n.link) { const path = n.link.replace(/^\//, "").split("/"); navigate(path[0] === "certificates" ? "profile" : path[0], path[1], path[2]); } else reload();
  };
  const save = async () => {
    try { await notifications.savePrefs(p); setSaved("Preferences saved."); setDraft(null); prefs.reload(); } catch (e) { setSaved((e as Error).message); }
  };
  const toggle = (k: "battles" | "achievements" | "reminders" | "projects", label: string) => (
    <label className="option" key={k}><input type="checkbox" checked={p[k]} onChange={(e) => setDraft({ ...p, [k]: e.target.checked })} /><span>{label}</span></label>
  );
  return (
    <div className="page">
      <header className="page-head"><div><h1>Notifications</h1><p className="muted">In-app only. We don't send push or email.</p></div>
        <Button variant="outline" onClick={markAll} disabled={data.unread === 0}>Mark all read</Button></header>
      <div className="split">
        <section className="card">
          {data.notifications.length === 0 && <Empty title="You're all caught up" />}
          {data.notifications.map((n) => (
            <div key={n.id} className={`notif ${n.read_at ? "" : "unread"}`}>
              <span className="dot" aria-hidden />
              <div><strong>{n.title}</strong><div className="muted small">{n.body}</div><div className="muted small">{formatDate(n.created_at)}</div></div>
              <Button size="sm" variant="ghost" onClick={() => open(n)}>{n.link ? "Open" : n.read_at ? "" : "Mark read"}</Button>
            </div>
          ))}
        </section>
        <aside className="card">
          <h3>Preferences</h3>
          <fieldset className="options"><legend className="sr-only">Notification types</legend>
            {toggle("battles", "Battle invitations & results")}{toggle("achievements", "Achievements & progress")}
            {toggle("reminders", "Study & revision reminders")}{toggle("projects", "Project updates")}
          </fieldset>
          <div className="inline-form" style={{ marginTop: 10 }}>
            <label className="field">Quiet from<input type="time" value={p.quiet_start ?? ""} onChange={(e) => setDraft({ ...p, quiet_start: e.target.value || null })} /></label>
            <label className="field">until<input type="time" value={p.quiet_end ?? ""} onChange={(e) => setDraft({ ...p, quiet_end: e.target.value || null })} /></label>
          </div>
          <p className="sticky-note">Reminders are held during quiet hours (server time). At most one revision reminder per chat per day.</p>
          <Button onClick={save} disabled={!draft}>Save preferences</Button>
          {saved && <p role="status" className="sticky-note">{saved}</p>}
        </aside>
      </div>
    </div>
  );
}
