import { useEffect, useState, type FormEvent } from "react";
import { ArrowLeft, Plus, Send, UserPlus } from "lucide-react";
import { get, post, patch, put } from "../api/client";
import { learn } from "../api/learn";
import { useLoad, navigate } from "../hooks";
import { Button, Badge } from "../components/ui";
import { ErrorBox, Loading, Empty, formatDate } from "../components/States";

interface Team {
  id: string;
  name: string;
  project_id: string;
  owner_id: string;
  submission?: string;
  submitted_at?: string;
  members: { user_id: string; name: string; project_role: string }[];
  tasks: { id: string; title: string; assignee_id: string | null; status: string; deadline: string | null }[];
  messages: { id: string; name: string; body: string; created_at: string }[];
  contributions: { id: string; name: string; action: string; created_at: string }[];
}

export default function TeamsPage({ id }: { id?: string }) {
  return id ? <Workspace key={id} id={id} /> : <Hub />;
}

function Hub() {
  const list = useLoad(() => get<{ teams: Team[]; invitations: { id: string; name: string }[] }>("/teams"));
  const projects = useLoad(learn.projects);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      list.reload();
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
          <div className="eyebrow">COLLABORATION // COHORT LEARNING</div>
          <h1>TEAM PROJECTS</h1>
          <p className="muted">
            Collaborate in teams of 4 or 5 students. Distribute engineering tasks, discuss architecture, and preserve individual contribution logs.
          </p>
        </div>
      </header>

      {error && <ErrorBox message={error} />}
      {list.error && <ErrorBox message={list.error} onRetry={list.reload} />}
      {list.loading && <Loading label="Loading your teams…" />}

      {/* Invitations */}
      {list.data?.invitations.map((i) => (
        <section
          className="card"
          key={i.id}
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 16,
            backgroundColor: "var(--color-amber-soft)",
          }}
        >
          <div>
            <div className="eyebrow" style={{ marginBottom: 4 }}>INVITATION RECEIVED</div>
            <h2 style={{ margin: 0 }}>Join Team {i.name}</h2>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <Button
              variant="primary"
              disabled={busy}
              onClick={() =>
                act(async () => {
                  const r = await post<{ team_id: string }>(`/teams/invitations/${i.id}/respond`, { accept: true });
                  navigate("teams", r.team_id);
                })
              }
            >
              Accept & Enter
            </Button>
            <Button
              variant="ghost"
              disabled={busy}
              onClick={() => act(() => post(`/teams/invitations/${i.id}/respond`, { accept: false }))}
            >
              Decline
            </Button>
          </div>
        </section>
      ))}

      {/* Existing Teams */}
      <section>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>YOUR ACTIVE TEAMS</h2>
          <span className="badge">{(list.data?.teams ?? []).length} REGISTERED</span>
        </div>
        <div className="grid-2">
          {list.data?.teams.map((t) => (
            <button
              className="card chat-tile"
              key={t.id}
              onClick={() => navigate("teams", t.id)}
              aria-label={`Open team ${t.name}`}
            >
              <div className="row-between">
                <h3 style={{ margin: 0 }}>{t.name}</h3>
                <Badge variant={t.submitted_at ? "success" : "default"}>
                  {t.submitted_at ? "SUBMITTED" : "IN PROGRESS"}
                </Badge>
              </div>
              <p className="muted small">Click to access shared board, team discussion, and member roles.</p>
            </button>
          ))}
        </div>
        {list.data?.teams.length === 0 && <Empty title="You are not part of any project teams yet" />}
      </section>

      {/* Create Team Form */}
      <form
        className="card"
        onSubmit={(e: FormEvent<HTMLFormElement>) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          act(async () => {
            const t = await post<Team>("/teams", {
              name: String(f.get("name")),
              project_id: String(f.get("project")),
            });
            navigate("teams", t.id);
          });
        }}
        style={{ marginTop: 24 }}
      >
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>CREATE NEW PROJECT TEAM</h2>
          <Badge variant="accent">OWNER PORTAL</Badge>
        </div>
        <label className="field">
          <span>Team Name</span>
          <input name="name" required minLength={2} maxLength={80} placeholder="e.g. Distributed Systems Squad" />
        </label>
        <label className="field">
          <span>Target Portfolio Project</span>
          <select name="project" required>
            {projects.data?.projects.map((p) => (
              <option value={p.id} key={p.id}>
                {p.subject_title} · {p.title} ({p.level})
              </option>
            ))}
          </select>
        </label>
        {projects.error && <ErrorBox message={projects.error} />}
        <Button type="submit" variant="primary" loading={busy} disabled={!projects.data}>
          Create Team & Open Workspace
        </Button>
      </form>
    </div>
  );
}

function Workspace({ id }: { id: string }) {
  const data = useLoad(() => get<Team>(`/teams/${id}`), [id]);
  const me = useLoad(() => get<{ id: string }>("/auth/me"));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const t = setInterval(data.reload, 15000);
    return () => clearInterval(t);
  }, [data.reload]);

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      data.reload();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!data.data && data.loading) return <Loading label="Loading team workspace…" />;
  if (data.error || !data.data) return <ErrorBox message={data.error ?? "Team unavailable"} onRetry={data.reload} />;

  const t = data.data;
  const owner = t.owner_id === me.data?.id;
  const completedTasks = t.tasks.filter((x) => x.status === "done").length;

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">TEAM WORKSPACE // {t.members.length} MEMBERS</div>
          <h1>{t.name.toUpperCase()}</h1>
          <p className="muted">
            {t.members.length}/5 students enrolled · {completedTasks}/{t.tasks.length} tasks completed
          </p>
        </div>
        <Button variant="ghost" leftIcon={ArrowLeft} onClick={() => navigate("teams")}>
          All Teams
        </Button>
      </header>

      {error && <ErrorBox message={error} />}
      {notice && <p className="sticky-note" role="status">{notice}</p>}

      <div className="split">
        {/* Left Column: Board & Discussion */}
        <section style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Shared Board */}
          <article className="card">
            <div className="row-between" style={{ marginBottom: 14 }}>
              <h2>SHARED PROJECT BOARD</h2>
              <span className="badge badge-primary">{completedTasks}/{t.tasks.length} DONE</span>
            </div>

            {t.tasks.length === 0 && (
              <p className="muted small">No tasks yet. Create the first task below to coordinate milestones.</p>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 20 }}>
              {t.tasks.map((task) => (
                <div
                  key={task.id}
                  className="row-between"
                  style={{
                    padding: "12px 14px",
                    border: "2px solid var(--border-strong)",
                    boxShadow: "var(--shadow-sm)",
                    borderRadius: "var(--radius-xs)",
                    backgroundColor: task.status === "done" ? "#F0FDF4" : "#FFFFFF",
                  }}
                >
                  <div>
                    <strong style={{ fontSize: "0.95rem" }}>{task.title}</strong>
                    <p className="muted small" style={{ margin: "2px 0 0" }}>
                      Assignee: {t.members.find((m) => m.user_id === task.assignee_id)?.name ?? "Unassigned"}{" "}
                      {task.deadline && `· Due ${formatDate(task.deadline)}`}
                    </p>
                  </div>
                  <div>
                    <select
                      aria-label={`Status of ${task.title}`}
                      value={task.status}
                      disabled={busy || (!!task.assignee_id && task.assignee_id !== me.data?.id && !owner)}
                      onChange={(e) => act(() => patch(`/teams/${id}/tasks/${task.id}`, { status: e.target.value }))}
                      style={{ padding: "6px 10px", width: "auto" }}
                    >
                      <option value="todo">TO DO</option>
                      <option value="doing">IN PROGRESS</option>
                      <option value="done">DONE ✓</option>
                    </select>
                  </div>
                </div>
              ))}
            </div>

            {/* Add Task */}
            <form
              onSubmit={(e: FormEvent<HTMLFormElement>) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                act(() =>
                  post(`/teams/${id}/tasks`, {
                    title: String(f.get("title")),
                    assignee_id: String(f.get("assignee")) || null,
                    deadline: f.get("deadline") ? new Date(String(f.get("deadline"))).toISOString() : null,
                  })
                );
                e.currentTarget.reset();
              }}
              style={{
                paddingTop: 16,
                borderTop: "1.5px dashed var(--border-strong)",
              }}
            >
              <h3 style={{ textTransform: "uppercase", fontSize: "0.85rem", marginBottom: 10 }}>Add Board Task</h3>
              <div className="grid-2">
                <label className="field">
                  <span>Task Title</span>
                  <input name="title" required minLength={2} placeholder="e.g. Implement LEGB parser" />
                </label>
                <label className="field">
                  <span>Assignee</span>
                  <select name="assignee">
                    <option value="">Unassigned</option>
                    {t.members.map((m) => (
                      <option key={m.user_id} value={m.user_id}>
                        {m.name} ({m.project_role})
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="field">
                <span>Deadline (Optional)</span>
                <input type="datetime-local" name="deadline" />
              </label>
              <Button type="submit" variant="secondary" size="sm" loading={busy} leftIcon={Plus}>
                Add Task to Board
              </Button>
            </form>
          </article>

          {/* Team Discussion */}
          <article className="card">
            <div className="row-between" style={{ marginBottom: 14 }}>
              <h2>TEAM DISCUSSION</h2>
              <span className="badge">REAL-TIME LOG</span>
            </div>

            <div style={{ maxHeight: 360, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10, marginBottom: 16 }}>
              {t.messages.length === 0 && (
                <p className="muted small">No messages yet. Post an update to start the discussion.</p>
              )}
              {t.messages.map((m) => (
                <div
                  key={m.id}
                  style={{
                    padding: "10px 14px",
                    border: "1.5px solid var(--border-strong)",
                    boxShadow: "var(--shadow-xs)",
                    borderRadius: "var(--radius-xs)",
                    backgroundColor: "#FFFFFF",
                  }}
                >
                  <div className="row-between" style={{ marginBottom: 4 }}>
                    <strong style={{ fontSize: "0.88rem" }}>{m.name}</strong>
                    <span className="muted small">{formatDate(m.created_at)}</span>
                  </div>
                  <p style={{ whiteSpace: "pre-wrap", margin: 0, fontSize: "0.92rem" }}>{m.body}</p>
                </div>
              ))}
            </div>

            <form
              onSubmit={(e: FormEvent<HTMLFormElement>) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                act(() => post(`/teams/${id}/messages`, { body: String(f.get("body")) }));
                e.currentTarget.reset();
              }}
            >
              <label className="field">
                <span>Post Message</span>
                <textarea name="body" required maxLength={4000} rows={2} placeholder="Share architectural ideas, blocker updates, or PR links…" />
              </label>
              <Button type="submit" variant="primary" size="sm" loading={busy} leftIcon={Send}>
                Post to Discussion
              </Button>
            </form>
          </article>

          {/* Final Submission by Owner */}
          {owner && (
            <form
              className="card"
              onSubmit={(e: FormEvent<HTMLFormElement>) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                act(async () => {
                  await post(`/teams/${id}/submit`, { text: String(f.get("text")) });
                  setNotice("Team evidence saved. Submission has been recorded in the platform ledger.");
                });
              }}
            >
              <div className="row-between" style={{ marginBottom: 10 }}>
                <h2>SUBMIT TEAM EVIDENCE</h2>
                <Badge variant="accent">OWNER ONLY</Badge>
              </div>
              <p className="muted small">
                Requires at least four members and all board tasks completed before evaluation.
              </p>
              <label className="field">
                <span>Team Documentation & Proof of Work</span>
                <textarea
                  name="text"
                  required
                  minLength={80}
                  rows={5}
                  defaultValue={t.submission ?? ""}
                  placeholder="Summarize team architectural achievements, individual responsibilities, and repository links…"
                />
              </label>
              <Button type="submit" variant="primary" loading={busy}>
                Submit Team Portfolio Evidence
              </Button>
            </form>
          )}
        </section>

        {/* Right Column: Members & Contributions */}
        <aside style={{ display: "flex", flexDirection: "column", gap: 24 }}>
          {/* Members Card */}
          <article className="card">
            <div className="row-between" style={{ marginBottom: 14 }}>
              <h2>ROSTER & ROLES</h2>
              <span className="badge">{t.members.length}/5</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {t.members.map((m) => (
                <div
                  key={m.user_id}
                  style={{
                    padding: "10px 12px",
                    border: "1.5px solid var(--border-strong)",
                    boxShadow: "var(--shadow-xs)",
                    borderRadius: "var(--radius-xs)",
                    backgroundColor: "#FAF9F5",
                  }}
                >
                  <strong style={{ display: "block" }}>{m.name}</strong>
                  {owner ? (
                    <div style={{ marginTop: 4 }}>
                      <input
                        aria-label={`Project role for ${m.name}`}
                        defaultValue={m.project_role}
                        maxLength={60}
                        onBlur={(e) => {
                          if (e.target.value !== m.project_role) {
                            act(() => put(`/teams/${id}/members/${m.user_id}/role`, { project_role: e.target.value }));
                          }
                        }}
                        style={{ padding: "4px 8px", fontSize: "0.82rem" }}
                      />
                    </div>
                  ) : (
                    <span className="badge" style={{ marginTop: 4 }}>{m.project_role}</span>
                  )}
                </div>
              ))}
            </div>

            {owner && t.members.length < 5 && (
              <form
                onSubmit={(e: FormEvent<HTMLFormElement>) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  act(async () => {
                    await post(`/teams/${id}/invitations`, { email: String(f.get("email")) });
                    setNotice("Invitation dispatched to their team hub.");
                  });
                  e.currentTarget.reset();
                }}
                style={{ marginTop: 16, paddingTop: 14, borderTop: "1.5px dashed var(--border-strong)" }}
              >
                <label className="field">
                  <span>Invite Student</span>
                  <input name="email" type="email" required placeholder="peer@college.edu" />
                </label>
                <Button type="submit" size="sm" variant="secondary" loading={busy} leftIcon={UserPlus}>
                  Send Team Invite
                </Button>
              </form>
            )}
          </article>

          {/* Contribution History */}
          <article className="card">
            <div className="row-between" style={{ marginBottom: 10 }}>
              <h2>CONTRIBUTIONS</h2>
              <span className="badge badge-accent">AUDIT TRAIL</span>
            </div>
            <p className="muted small">
              Verified logs record individual commits and task completions without fabricating ratings.
            </p>
            <div style={{ maxHeight: 320, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
              {t.contributions.map((c) => (
                <div
                  key={c.id}
                  style={{
                    padding: "8px 10px",
                    borderLeft: "3px solid var(--border-strong)",
                    backgroundColor: "#FAF9F5",
                    fontSize: "0.85rem",
                  }}
                >
                  <strong>{c.name}</strong> · {c.action.replaceAll("_", " ")}
                  <div className="muted small">{formatDate(c.created_at)}</div>
                </div>
              ))}
              {t.contributions.length === 0 && <p className="muted small">No contribution events recorded yet.</p>}
            </div>
          </article>
        </aside>
      </div>
    </div>
  );
}
