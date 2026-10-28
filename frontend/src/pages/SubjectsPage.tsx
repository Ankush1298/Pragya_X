import { useState } from "react";
import { ArrowRight, Cloud, Code, Database, Globe, Lock, Sparkles } from "lucide-react";
import { api } from "../api/client";
import { ErrorBox, Loading } from "../components/States";
import { Button, Badge } from "../components/ui";
import { navigate, useLoad } from "../hooks";

const ICONS: Record<string, typeof Code> = {
  python: Code,
  globe: Globe,
  database: Database,
  cloud: Cloud,
};

export default function SubjectsPage() {
  const { data, error, loading, reload, setData } = useLoad(api.subjects);
  const [saving, setSaving] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  if (loading) return <Loading label="Loading curriculum subjects…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  const select = async (id: string) => {
    setSaving(id);
    setSaveError(null);
    try {
      const s = await api.selectSubject(id);
      setData({ ...data, selected_subject_id: s.id });
      setSaved(true);
    } catch (e) {
      setSaveError((e as Error).message);
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <div className="eyebrow">CURRICULUM TRACKS // SPECIALIZATION</div>
          <h1>CHOOSE YOUR SUBJECT TRACK</h1>
          <p className="muted">
            Your selected track configures your diagnostics, recommendations, and AI mentor context.
          </p>
        </div>
        {saved && (
          <Button
            variant="primary"
            leftIcon={Sparkles}
            rightIcon={ArrowRight}
            onClick={() => navigate("assessment")}
          >
            Start Diagnostic Assessment
          </Button>
        )}
      </header>

      {saveError && <ErrorBox message={saveError} />}
      {saved && (
        <div className="alert alert-success" role="status">
          <strong>Subject Selected!</strong> Your profile has been updated. You can proceed directly to the diagnostic assessment.
        </div>
      )}

      <div className="grid-2">
        {data.subjects.map((s) => {
          const Icon = ICONS[s.icon] ?? Code;
          const selected = data.selected_subject_id === s.id;

          return (
            <article
              key={s.id}
              className={`card ${selected ? "selected" : ""}`}
              style={{
                borderColor: selected ? "var(--border-strong)" : undefined,
                backgroundColor: selected ? "#FFFFF5" : "#FFFFFF",
                boxShadow: selected ? "var(--shadow-lg)" : "var(--shadow-md)",
                borderWidth: selected ? 3 : 2,
                display: "flex",
                flexDirection: "column",
                gap: 12,
              }}
            >
              <div className="row-between">
                <div
                  style={{
                    width: 48,
                    height: 48,
                    backgroundColor: selected ? "var(--brand-gradient)" : "var(--bg-secondary)",
                    border: "2px solid var(--border-strong)",
                    boxShadow: "2px 2px 0 var(--border-strong)",
                    borderRadius: "var(--radius-xs)",
                    display: "grid",
                    placeItems: "center",
                    color: selected ? "#FFFFFF" : "var(--text-primary)",
                  }}
                >
                  <Icon size={24} aria-hidden />
                </div>
                {selected ? (
                  <span className="badge badge-primary">ACTIVE SELECTION ✓</span>
                ) : s.is_active ? (
                  <Badge variant="accent">READY</Badge>
                ) : (
                  <Badge variant="soon">COMING SOON</Badge>
                )}
              </div>

              <h2 style={{ fontSize: "1.4rem", margin: 0 }}>{s.title}</h2>
              <p className="muted" style={{ minHeight: 48, fontSize: "0.95rem" }}>
                {s.description}
              </p>

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "6px 0 12px" }}>
                {s.is_active ? (
                  <>
                    <span className="badge">{s.question_count} Questions</span>
                    <Badge variant="default">{s.difficulty}</Badge>
                    <span className="badge badge-success">Server Evaluated</span>
                  </>
                ) : (
                  <span className="badge badge-soon">
                    <Lock size={12} style={{ verticalAlign: "middle", marginRight: 4 }} aria-hidden /> In Curriculum Development
                  </span>
                )}
              </div>

              <div style={{ marginTop: "auto" }}>
                <Button
                  variant={selected ? "outline" : "primary"}
                  block
                  disabled={!s.is_active || saving !== null}
                  loading={saving === s.id}
                  onClick={() => select(s.id)}
                  aria-pressed={selected}
                >
                  {!s.is_active
                    ? "Track Not Available Yet"
                    : saving === s.id
                    ? "Updating Profile…"
                    : selected && saved
                    ? "Selected & Ready ✓"
                    : selected
                    ? "Currently Active Track"
                    : "Select This Curriculum"}
                </Button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
