import { useState } from "react";
import { Sparkles } from "lucide-react";
import { learn, type Project } from "../api/learn";
import { useLoad } from "../hooks";
import { Button, Badge, Card } from "../components/ui";
import { ErrorBox, Empty, Loading } from "../components/States";

function ProjectCard({ project, refresh }: { project: Project; refresh: () => void }) {
  const [text, setText] = useState(project.submission_text ?? "");
  const [url, setUrl] = useState(project.submission_url ?? "");
  const [scores, setScores] = useState<Record<string, number>>(project.reflection_scores ?? {});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doneCount = project.milestones_done.length;
  const totalMilestones = project.milestones.length;
  const progressPct = Math.round((doneCount / Math.max(totalMilestones, 1)) * 100);

  return (
    <Card>
      <div className="page-head" style={{ marginBottom: 14 }}>
        <div>
          <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
            <Badge
              variant={
                project.level === "Extreme"
                  ? "accent"
                  : project.level === "Advanced"
                  ? "primary"
                  : "default"
              }
            >
              {project.level.toUpperCase()}
            </Badge>
            <span className="muted small">{project.subject_title}</span>
          </div>
          <h2 style={{ fontSize: "1.35rem", margin: 0 }}>{project.title}</h2>
        </div>
        <span
          className="badge"
          style={{
            backgroundColor: project.status === "submitted" ? "var(--color-amber)" : "var(--bg-secondary)",
            color: project.status === "submitted" ? "#FFFFFF" : "var(--text-primary)",
            fontWeight: 800,
          }}
        >
          {project.status.replaceAll("_", " ").toUpperCase()}
        </span>
      </div>

      <p style={{ fontSize: "0.95rem", lineHeight: 1.5 }}>{project.objective}</p>

      <div style={{ margin: "10px 0" }}>
        <strong className="small" style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Target Skills:
        </strong>{" "}
        <span className="muted small">{project.skills.join(", ")}</span>
      </div>

      {/* Milestones */}
      <div style={{ margin: "16px 0", padding: "14px", backgroundColor: "#FAF9F5", border: "1.5px solid var(--border-strong)", borderRadius: "var(--radius-xs)" }}>
        <div className="row-between" style={{ marginBottom: 8 }}>
          <strong style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Project Milestones ({doneCount}/{totalMilestones})
          </strong>
          <span className="small" style={{ fontWeight: 800 }}>{progressPct}%</span>
        </div>
        <div className="progress" style={{ height: 8, margin: "6px 0 12px" }}>
          <div className="progress-fill" style={{ width: `${progressPct}%` }} />
        </div>
        {project.milestones.map((m, i) => (
          <label className="option" key={i} style={{ margin: "6px 0", padding: "10px 14px", backgroundColor: "#FFFFFF" }}>
            <input
              type="checkbox"
              checked={project.milestones_done.includes(i)}
              disabled={busy}
              onChange={(e) => act(() => learn.milestone(project.id, i, e.target.checked))}
            />
            <span style={{ fontSize: "0.88rem", fontWeight: project.milestones_done.includes(i) ? 500 : 700 }}>
              {m}
            </span>
          </label>
        ))}
      </div>

      <div style={{ margin: "12px 0", fontSize: "0.88rem" }}>
        <strong>Deliverables:</strong> <span className="muted">{project.deliverables}</span>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          act(() =>
            learn.submitProject(project.id, {
              text,
              url: url || undefined,
              rubric_scores: Object.fromEntries(project.rubric.map((c) => [c, scores[c] ?? 0])),
            })
          );
        }}
        style={{ marginTop: 18 }}
      >
        <label className="field">
          <span>Your Work & Engineering Reflection</span>
          <textarea
            required
            minLength={80}
            rows={5}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Document your architecture, implementation challenges, test results, and core takeaways…"
          />
        </label>

        <label className="field">
          <span>Portfolio Evidence / Repository Link (Optional)</span>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/your-username/project-repo"
          />
        </label>

        <div style={{ margin: "18px 0", padding: 14, backgroundColor: "var(--bg-secondary)", border: "1.5px solid var(--border-strong)", borderRadius: "var(--radius-xs)" }}>
          <div className="row-between" style={{ marginBottom: 6 }}>
            <h3 style={{ fontSize: "0.95rem", textTransform: "uppercase", margin: 0 }}>Self-Assessment Rubric</h3>
            <span className="badge">Portfolio Evidence</span>
          </div>
          <p className="muted small" style={{ margin: "0 0 12px" }}>
            Assess each criterion honestly. Scores are permanently preserved in your verifiable skill profile.
          </p>
          {project.rubric.map((criterion, i) => (
            <label className="field" key={i} style={{ marginBottom: 10 }}>
              <span>{criterion}</span>
              <select
                value={scores[criterion] ?? 0}
                onChange={(e) => setScores({ ...scores, [criterion]: Number(e.target.value) })}
              >
                {[0, 1, 2, 3].map((n) => (
                  <option key={n} value={n}>
                    {n} / 3 — {n === 3 ? "Exemplary" : n === 2 ? "Proficient" : n === 1 ? "Developing" : "Not Attempted"}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>

        {error && <ErrorBox message={error} />}

        <Button type="submit" variant="primary" loading={busy} block>
          Save Project Submission to Portfolio
        </Button>

        {project.evaluation_note && (
          <p className="sticky-note" style={{ marginTop: 14 }}>
            <Sparkles size={14} aria-hidden /> {project.evaluation_note}
          </p>
        )}
      </form>
    </Card>
  );
}

export default function ProjectsPage() {
  const { data, error, loading, reload } = useLoad(learn.projects);
  const [subject, setSubject] = useState("");

  if (loading) return <Loading label="Loading skill portfolio projects…" />;
  if (error || !data) return <ErrorBox message={error ?? "Projects unavailable"} onRetry={reload} />;

  const filtered = data.projects.filter((p) => !subject || p.subject_title === subject);

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">PORTFOLIO EVIDENCE // PRACTICAL LABS</div>
          <h1>BUILD YOUR SKILL PORTFOLIO</h1>
          <p className="muted">
            Practical hands-on projects spanning Basic to Extreme tiers, with verified milestone tracking and self-reflection rubrics.
          </p>
        </div>
        <div>
          <label className="sr-only" htmlFor="project-filter">Filter by subject</label>
          <select
            id="project-filter"
            aria-label="Filter projects by subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            style={{ minWidth: 200 }}
          >
            <option value="">All Subjects</option>
            {Array.from(new Set(data.projects.map((p) => p.subject_title))).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </header>

      {data.projects.length === 0 && <Empty title="No projects currently published" />}

      <div className="grid-2">
        {filtered.map((p) => (
          <ProjectCard key={p.id} project={p} refresh={reload} />
        ))}
      </div>
    </div>
  );
}
