import { useState } from "react";
import { Award, Copy, Download, Gift, Share2, ShieldCheck } from "lucide-react";
import { growth, learn, notifications, type Cert, type Prefs } from "../api/learn";
import { API_BASE } from "../api/client";
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
      setMsg("Verification share text copied to clipboard!");
      setTimeout(() => setMsg(null), 2500);
    } catch {
      setMsg("Copy failed; use the verification link directly.");
    }
  };

  return (
    <Card style={{ position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 4, background: "var(--brand-gradient)" }} />
      <div className="row-between" style={{ marginBottom: 8 }}>
        <strong style={{ fontSize: "1.1rem" }}>{c.title}</strong>
        <Badge variant="accent">{c.cert_type.replace("_", " ")}</Badge>
      </div>
      <p className="muted small">{c.description}</p>
      <div style={{ margin: "10px 0", padding: "8px 10px", background: "#FAF9F5", border: "1px solid var(--border-strong)", borderRadius: "var(--radius-xs)" }}>
        <span className="small muted">Verification Key: </span>
        <code style={{ fontSize: "0.82rem" }}>{c.verification_id}</code>
      </div>
      <div className="actions" style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
        <a
          className="btn btn-outline btn-sm"
          href={`${API_BASE}/api/certificates/${encodeURIComponent(c.verification_id)}/download`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Download size={14} aria-hidden /> View / Print PDF
        </a>
        <Button size="sm" variant="ghost" leftIcon={Share2} onClick={share}>
          Copy Share Text
        </Button>
        <Button size="sm" variant="ghost" onClick={() => navigate("verify", c.verification_id)}>
          Verify Signature
        </Button>
      </div>
      {msg && <p className="sticky-note" role="status" style={{ marginTop: 10 }}>{msg}</p>}
    </Card>
  );
}

export function ProfilePage() {
  const { data, error, loading, reload } = useLoad(learn.skillProfile);
  if (loading) return <Loading label="Generating verified skill profile…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;
  const g = data.gamification;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">VERIFIABLE CREDENTIALS // PORTFOLIO</div>
          <h1>SKILL PROFILE & CREDENTIALS</h1>
          <p className="muted">Objective evidence of what you have actually studied, coded, and achieved on PragyaX.</p>
        </div>
      </header>

      <div className="notice-demo" style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <ShieldCheck size={18} aria-hidden />
        <span>{data.disclaimer}</span>
      </div>

      <section className="stats">
        <div className="stat card">
          <span className="stat-label">TOTAL XP</span>
          <span className="stat-value">{g.total_xp}</span>
          <span className="muted small">Level {g.level} · {g.title}</span>
        </div>
        <div className="stat card">
          <span className="stat-label">LEARNING STREAK</span>
          <span className="stat-value">{g.streak.current_streak} DAYS</span>
          <span className="muted small">Best streak: {g.streak.longest_streak} days</span>
        </div>
        <div className="stat card">
          <span className="stat-label">ARENA BATTLES</span>
          <span className="stat-value">{g.battle_stats.wins}W</span>
          <span className="muted small">{g.battle_stats.losses} lost · {g.battle_stats.ties} tied</span>
        </div>
        <div className="stat card">
          <span className="stat-label">ACHIEVEMENTS</span>
          <span className="stat-value">{data.certificates.length}</span>
          <span className="muted small">{data.badges.length} verified badges</span>
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>SUBJECT TRACKS MASTERED</h2>
          <span className="badge badge-primary">{data.subjects.length} ENROLLED</span>
        </div>
        {data.subjects.length === 0 && (
          <Empty title="No curriculum subjects started yet">
            <Button variant="primary" onClick={() => navigate("learn")}>Start a Learning Chat</Button>
          </Empty>
        )}
        <div className="chat-grid">
          {data.subjects.map((s) => (
            <button key={s.chat_id} className="card chat-tile" onClick={() => navigate("learn", s.chat_id)}>
              <div className="row-between">
                <h3 style={{ margin: 0 }}>{s.subject_title}</h3>
                {s.level && <span className={levelClass(s.level)}>{s.level}</span>}
              </div>
              {s.curated ? (
                <ProgressBar
                  value={s.modules_total ? (100 * s.modules_completed) / s.modules_total : 0}
                  label={`${s.modules_completed}/${s.modules_total} modules`}
                />
              ) : (
                <span className="muted small">Mentor-only open dialogue</span>
              )}
              {s.improvement && (
                <span className={s.improvement.delta >= 0 ? "pill-ok small" : "pill-bad small"} style={{ fontWeight: 800 }}>
                  {s.improvement.delta >= 0 ? "+" : ""}{s.improvement.delta} pts measured delta
                </span>
              )}
              {s.mastered_topics.length > 0 && (
                <span className="small">Mastered: {s.mastered_topics.map((m) => m.title).join(", ")}</span>
              )}
              {s.weaknesses.length > 0 && (
                <span className="muted small">Working on: {s.weaknesses.slice(0, 3).join(", ")}</span>
              )}
            </button>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>PORTFOLIO LAB SUBMISSIONS</h2>
          <a href="#/projects" className="btn btn-outline btn-sm">Browse Lab Catalog</a>
        </div>
        {data.projects.length === 0 ? (
          <p className="muted">No submitted projects recorded. Complete project rubrics to display here.</p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Project Title</th>
                  <th>Level</th>
                  <th>Self-Rating Score</th>
                  <th>Evidence Status</th>
                </tr>
              </thead>
              <tbody>
                {data.projects.map((p) => (
                  <tr key={p.id}>
                    <td><strong>{p.title}</strong></td>
                    <td><span className="badge">{p.level}</span></td>
                    <td><strong>{p.rubric_total}/{p.rubric_max}</strong></td>
                    <td><Badge variant="warning">{p.evidence_type}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section style={{ marginTop: 28 }}>
        <div className="row-between" style={{ marginBottom: 10 }}>
          <h2 style={{ display: "flex", alignItems: "center", gap: 8, margin: 0 }}>
            <Award size={20} style={{ color: "var(--color-gold)" }} aria-hidden /> CERTIFICATES & RECOGNITION
          </h2>
          <span className="badge badge-accent">AUTHENTICATED RECORDS</span>
        </div>
        <p className="muted small" style={{ marginBottom: 16 }}>
          "PragyaX Challenge Achievement" records are issued cryptographically by this platform for proven mastery. They are verifiable anywhere via public ID.
        </p>

        {data.badges.length > 0 && (
          <div className="chips" style={{ marginBottom: 20 }}>
            {data.badges.map((b) => (
              <Badge key={b.badge_key} variant="primary" title={b.description} style={{ padding: "6px 12px" }}>
                {b.title}
              </Badge>
            ))}
          </div>
        )}

        {data.certificates.length === 0 && (
          <Empty title="No certificates issued yet">
            <p className="muted">Win an arena battle, finish a curriculum roadmap, or rank in a hosted tournament.</p>
          </Empty>
        )}
        <div className="grid-2">
          {data.certificates.map((c) => (
            <CertCard key={c.verification_id} c={c} />
          ))}
        </div>
      </section>
    </div>
  );
}

/* ------------------------------------------------------------------ Public verification */
export function VerifyPage({ id }: { id?: string }) {
  const [input, setInput] = useState(id ?? "");
  const { data, error, loading } = useLoad(() => (id ? growth.verify(id) : Promise.resolve(null)), [id]);

  return (
    <div className="page narrow" style={{ margin: "40px auto", padding: "0 20px" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <a className="brand brand-lg" href="#/">
          Pragya<span className="brand-x">X</span>
        </a>
        <div className="eyebrow" style={{ marginTop: 12 }}>PUBLIC VERIFICATION PORTAL</div>
        <h1>VERIFY AN ACHIEVEMENT</h1>
        <p className="muted">Enter a PragyaX verification ID to audit official issued credentials.</p>
      </div>

      <form
        className="card"
        onSubmit={(e) => {
          e.preventDefault();
          if (input.trim()) navigate("verify", input.trim());
        }}
      >
        <label className="field">
          <span>Verification Identifier</span>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. PRAGYA-CERT-940B-XXXX"
            required
          />
        </label>
        <Button type="submit" variant="primary" block>
          Verify Certificate Authenticity
        </Button>
      </form>

      {id && loading && <Loading label="Validating signature against ledger…" />}
      {id && error && (
        <div className="alert alert-error" role="alert" style={{ marginTop: 16 }}>
          <strong>Signature Invalid or Unrecognized.</strong> {error}
        </div>
      )}

      {data?.is_valid && (
        <Card style={{ marginTop: 24, border: "3px solid var(--border-strong)", boxShadow: "var(--shadow-lg)" }}>
          <div className="row-between" style={{ marginBottom: 12 }}>
            <Badge variant="success">✓ SIGNATURE VERIFIED AUTHENTIC</Badge>
            <span className="muted small">PLATFORM RECORD</span>
          </div>
          <h2 style={{ fontSize: "1.5rem", margin: "8px 0" }}>{data.title}</h2>
          <p style={{ fontSize: "1.05rem" }}>
            Awarded to <strong style={{ color: "var(--text-primary)" }}>{data.recipient_name}</strong>
          </p>
          <p className="muted">{data.description}</p>
          <p className="sticky-note">
            Official PragyaX achievement record. Issued on {data.issued_at && formatDate(data.issued_at)}. Verified independently.
          </p>
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

  if (loading) return <Loading label="Loading referral program…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(data.referral_code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard fallback */
    }
  };

  const apply = async () => {
    try {
      const r = await growth.applyReferral(code.trim());
      setMsg({ ok: true, text: r.message });
      reload();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">GROWTH // PEER REFERRALS</div>
          <h1>INVITE FRIENDS & EARN XP</h1>
          <p className="muted">{data.reward_rule}</p>
        </div>
      </header>

      <div className="grid-2">
        <Card>
          <h2>YOUR INVITATION CODE</h2>
          <p className="muted small">Share this code with fellow students during sign-up.</p>
          <div
            style={{
              padding: "16px 20px",
              background: "var(--brand-gradient)",
              border: "2px solid var(--border-strong)",
              boxShadow: "var(--shadow-sm)",
              fontFamily: "var(--font-mono)",
              fontSize: "1.4rem",
              fontWeight: 800,
              letterSpacing: "0.08em",
              textAlign: "center",
              margin: "12px 0",
              color: "#FFFFFF",
            }}
          >
            {data.referral_code}
          </div>
          <Button leftIcon={Copy} variant="primary" block onClick={copy}>
            {copied ? "Invitation Code Copied!" : "Copy Invitation Code"}
          </Button>
          <p className="sticky-note" style={{ marginTop: 14 }}>
            Referrals unlock XP once your friend completes both their diagnostic and first lesson, maintaining academic honesty.
          </p>
        </Card>

        <Card>
          <h2>GOT A FRIEND'S INVITE CODE?</h2>
          <p className="muted small">Claim your starter bonus before finishing your first module.</p>
          <div className="inline-form" style={{ marginTop: 14 }}>
            <label className="sr-only" htmlFor="ref-code">Referral code</label>
            <input
              id="ref-code"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="PRAGYAX-XXXXXX"
            />
            <Button variant="secondary" onClick={apply} disabled={!code.trim()}>
              Apply Code
            </Button>
          </div>
          {msg && (
            <p className={msg.ok ? "pill-ok" : "pill-bad"} role="status" style={{ marginTop: 12, padding: "8px 12px", borderRadius: 2 }}>
              {msg.text}
            </p>
          )}
        </Card>
      </div>

      <section className="stats" style={{ marginTop: 16 }}>
        <div className="stat card">
          <span className="stat-label">TOTAL INVITED</span>
          <span className="stat-value">{data.total_invited}</span>
        </div>
        <div className="stat card">
          <span className="stat-label">PENDING LESSON</span>
          <span className="stat-value">{data.pending_referrals}</span>
        </div>
        <div className="stat card">
          <span className="stat-label">COMPLETED & REWARDED</span>
          <span className="stat-value">{data.successful_referrals}</span>
        </div>
        <div className="stat card">
          <span className="stat-label">BONUS XP GAINED</span>
          <span className="stat-value">{data.xp_earned_from_referrals}</span>
          <span className="muted small">+{data.referrer_xp} XP per learner</span>
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <h2>REFERRAL LOG</h2>
        {data.referral_history.length === 0 ? (
          <Empty title="No referrals registered yet" />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Student Learner</th>
                  <th>Reward Status</th>
                  <th>Invited Date</th>
                </tr>
              </thead>
              <tbody>
                {data.referral_history.map((r) => (
                  <tr key={r.id}>
                    <td><strong>{r.referee_name}</strong></td>
                    <td>
                      <Badge variant={r.status === "REWARDED" ? "success" : "warning"}>
                        {r.status}
                      </Badge>
                    </td>
                    <td>{formatDate(r.created_at)}</td>
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

/* ------------------------------------------------------------------ Rewards & XP ledger */
export function RewardsPage() {
  const profile = useLoad(growth.profile);
  const ledger = useLoad(growth.ledger);
  const rewards = useLoad(growth.rewards);
  const [msg, setMsg] = useState<string | null>(null);

  if (profile.loading || ledger.loading || rewards.loading) return <Loading label="Loading rewards ledger…" />;
  if (profile.error || !profile.data) return <ErrorBox message={profile.error ?? "No data"} onRetry={profile.reload} />;

  const p = profile.data;
  const redeem = async (id: string) => {
    try {
      await growth.redeem(id);
      setMsg("Demo reward redeemed (XP deducted, demonstrated ledger transaction).");
      profile.reload();
      ledger.reload();
      rewards.reload();
    } catch (e) {
      setMsg((e as Error).message);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">ECONOMY // REWARDS & XP</div>
          <h1>REWARDS & XP LEDGER</h1>
          <p className="muted">XP is awarded permanently on the server for genuine educational milestones.</p>
        </div>
      </header>

      <section className="stats">
        <div className="stat card">
          <span className="stat-label">TOTAL XP BALANCE</span>
          <span className="stat-value">{p.total_xp}</span>
          <span className="muted small">Level {p.level} · {p.title}</span>
        </div>
        <div className="stat card">
          <span className="stat-label">NEXT LEVEL THRESHOLD</span>
          <span className="stat-value">{p.next_threshold} XP</span>
          <ProgressBar value={p.progress_percentage} label="Level progress" />
        </div>
      </section>

      <div className="notice-demo" style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Gift size={18} aria-hidden />
        <div>
          <strong>Demo Sandbox Rewards.</strong>
          <span> There is no physical merchandise shipment; redeeming demonstrates transactional XP deduction.</span>
        </div>
      </div>

      {msg && <p role="status" className="sticky-note">{msg}</p>}

      <section>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>AVAILABLE DEMO REWARDS</h2>
          <span className="badge badge-primary">SIMULATED STORE</span>
        </div>
        <div className="chat-grid">
          {(rewards.data ?? []).map((r) => (
            <Card key={r.id} className="chat-tile">
              <div className="row-between">
                <h3 style={{ margin: 0 }}>{r.title}</h3>
                <Badge variant="demo">DEMO ITEM</Badge>
              </div>
              <p className="muted small">{r.description}</p>
              <div style={{ marginTop: "auto" }}>
                <Button
                  size="sm"
                  variant={r.can_afford ? "primary" : "outline"}
                  block
                  disabled={!r.can_afford}
                  onClick={() => redeem(r.id)}
                >
                  {r.can_afford ? `Redeem Reward · ${r.xp_cost} XP` : `${r.shortfall} XP Remaining`}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </section>

      <section style={{ marginTop: 24 }}>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>XP TRANSACTION AUDIT LEDGER</h2>
          <span className="badge">IMMUTABLE LOG</span>
        </div>
        {(ledger.data ?? []).length === 0 ? (
          <Empty title="No XP transactions recorded yet" />
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Educational Event / Reason</th>
                  <th style={{ textAlign: "right" }}>XP Impact</th>
                </tr>
              </thead>
              <tbody>
                {(ledger.data ?? []).map((e) => (
                  <tr key={e.id}>
                    <td>{formatDate(e.created_at)}</td>
                    <td><strong>{e.reason}</strong></td>
                    <td style={{ textAlign: "right" }}>
                      <span className={e.points_delta < 0 ? "pill-bad" : "pill-ok"} style={{ fontWeight: 800 }}>
                        {e.points_delta > 0 ? "+" : ""}{e.points_delta} XP
                      </span>
                    </td>
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

/* ------------------------------------------------------------------ Notifications */
export function NotificationsPage({ onChange }: { onChange: () => void }) {
  const { data, error, loading, reload } = useLoad(notifications.list);
  const prefs = useLoad(notifications.prefs);
  const [saved, setSaved] = useState<string | null>(null);
  const [draft, setDraft] = useState<Prefs | null>(null);

  if (loading || prefs.loading) return <Loading label="Loading notification center…" />;
  if (error || prefs.error || !data || !prefs.data)
    return <ErrorBox message={error ?? prefs.error ?? "Preferences unavailable"} onRetry={() => { reload(); prefs.reload(); }} />;

  const p = draft ?? prefs.data;
  const markAll = async () => {
    await notifications.read();
    reload();
    onChange();
  };

  const open = async (n: { id: string; link: string | null; read_at: string | null }) => {
    if (!n.read_at) {
      await notifications.read(n.id);
      onChange();
    }
    if (n.link) {
      const path = n.link.replace(/^\//, "").split("/");
      navigate(path[0] === "certificates" ? "profile" : path[0], path[1], path[2]);
    } else {
      reload();
    }
  };

  const save = async () => {
    try {
      await notifications.savePrefs(p);
      setSaved("Preferences successfully saved.");
      setDraft(null);
      prefs.reload();
    } catch (e) {
      setSaved((e as Error).message);
    }
  };

  const toggle = (k: "battles" | "achievements" | "reminders" | "projects", label: string) => (
    <label className="option" key={k} style={{ margin: "6px 0", backgroundColor: "#FFFFFF" }}>
      <input type="checkbox" checked={p[k]} onChange={(e) => setDraft({ ...p, [k]: e.target.checked })} />
      <span style={{ fontSize: "0.9rem" }}>{label}</span>
    </label>
  );

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">COMMUNICATIONS // IN-APP ALERTS</div>
          <h1>NOTIFICATIONS & PREFERENCES</h1>
          <p className="muted">In-app notifications only. PragyaX does not send marketing spam or external push messages.</p>
        </div>
        <Button variant="outline" onClick={markAll} disabled={data.unread === 0}>
          Mark All As Read
        </Button>
      </header>

      <div className="split">
        {/* Alerts List */}
        <section className="card">
          <div className="row-between" style={{ marginBottom: 14 }}>
            <h2>INBOX ({data.unread} UNREAD)</h2>
            <Badge variant="primary">LIVE FEED</Badge>
          </div>
          {data.notifications.length === 0 && <Empty title="You are all caught up!" />}
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {data.notifications.map((n) => (
              <div
                key={n.id}
                className="row-between"
                style={{
                  padding: "12px 16px",
                  border: "2px solid var(--border-strong)",
                  boxShadow: "var(--shadow-sm)",
                  borderRadius: "var(--radius-xs)",
                  backgroundColor: n.read_at ? "#FFFFFF" : "#FFFFF5",
                  borderLeft: n.read_at ? "2px solid var(--border-strong)" : "6px solid var(--color-amber)",
                }}
              >
                <div>
                  <strong>{n.title}</strong>
                  <div className="muted small" style={{ margin: "2px 0 4px" }}>{n.body}</div>
                  <div className="muted small" style={{ fontSize: "0.75rem" }}>{formatDate(n.created_at)}</div>
                </div>
                <Button size="sm" variant={n.link ? "primary" : "ghost"} onClick={() => open(n)}>
                  {n.link ? "View" : n.read_at ? "Read" : "Mark Read"}
                </Button>
              </div>
            ))}
          </div>
        </section>

        {/* Preferences */}
        <aside className="card">
          <h2>STUDY ALERT PREFERENCES</h2>
          <p className="muted small" style={{ margin: "0 0 14px" }}>
            Configure alerts for multiplayer battles, achievements, and spaced repetition reminders.
          </p>
          <fieldset className="options" style={{ margin: 0 }}>
            {toggle("battles", "Battle invitations & duel results")}
            {toggle("achievements", "Milestones, badges & certificates")}
            {toggle("reminders", "Spaced revision & study streak")}
            {toggle("projects", "Team project board updates")}
          </fieldset>

          <div className="grid-2" style={{ marginTop: 16 }}>
            <label className="field">
              <span>Quiet Hours From</span>
              <input
                type="time"
                value={p.quiet_start ?? ""}
                onChange={(e) => setDraft({ ...p, quiet_start: e.target.value || null })}
              />
            </label>
            <label className="field">
              <span>Until</span>
              <input
                type="time"
                value={p.quiet_end ?? ""}
                onChange={(e) => setDraft({ ...p, quiet_end: e.target.value || null })}
              />
            </label>
          </div>
          <p className="sticky-note">
            Quiet hours suppress study reminders. At most one revision nudge per chat per day.
          </p>
          <Button onClick={save} variant="primary" disabled={!draft} block>
            Save Alert Preferences
          </Button>
          {saved && <p role="status" className="sticky-note" style={{ marginTop: 10 }}>{saved}</p>}
        </aside>
      </div>
    </div>
  );
}
