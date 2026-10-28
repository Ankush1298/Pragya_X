import { useState, type FormEvent } from "react";
import { Bell } from "lucide-react";
import { api, patch } from "../api/client";
import { useLoad, navigate } from "../hooks";
import { Button, Badge } from "../components/ui";
import { ErrorBox, Loading, formatDate } from "../components/States";

export default function SettingsPage({ onSaved }: { onSaved: () => void }) {
  const me = useLoad(api.me);
  const [name, setName] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  if (me.loading) return <Loading label="Loading account profile…" />;
  if (me.error || !me.data) return <ErrorBox message={me.error ?? "Account unavailable"} onRetry={me.reload} />;

  const user = me.data;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await patch("/auth/profile", { name: name ?? user.name });
      setMessage("Profile changes saved successfully.");
      me.reload();
      onSaved();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page narrow">
      <header className="page-head">
        <div>
          <div className="eyebrow">ACCOUNT // PREFERENCES</div>
          <h1>ACCOUNT SETTINGS</h1>
          <p className="muted">Manage your personal learner identity, credentials, and notification schedules.</p>
        </div>
      </header>

      <form className="card" onSubmit={submit}>
        <div className="row-between" style={{ marginBottom: 14 }}>
          <h2>PERSONAL IDENTITY</h2>
          <Badge variant="primary">{user.is_admin ? "ADMINISTRATOR" : "STUDENT"}</Badge>
        </div>

        <label className="field">
          <span>Display Full Name</span>
          <input
            minLength={2}
            maxLength={100}
            required
            value={name ?? user.name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>

        <label className="field">
          <span>Primary Email Address</span>
          <input readOnly type="email" value={user.email} style={{ backgroundColor: "var(--bg-secondary)" }} />
        </label>

        <p className="muted small" style={{ margin: "4px 0 16px" }}>
          Joined PragyaX on {formatDate(user.created_at)} · User ID: <code>{user.id}</code>
        </p>

        {message && <p role="status" className="sticky-note">{message}</p>}

        <Button type="submit" variant="primary" loading={busy}>
          Save Profile Updates
        </Button>
      </form>

      <section className="card">
        <div className="row-between" style={{ marginBottom: 8 }}>
          <h2>STUDY ALERT SCHEDULES</h2>
          <Badge variant="accent">NOTIFICATIONS</Badge>
        </div>
        <p className="muted small">
          Control quiet hours, battle duel invitations, spaced revision prompts, and milestone achievement alerts.
        </p>
        <div style={{ marginTop: 14 }}>
          <Button variant="outline" leftIcon={Bell} onClick={() => navigate("notifications")}>
            Manage Alert Schedules
          </Button>
        </div>
      </section>
    </div>
  );
}
