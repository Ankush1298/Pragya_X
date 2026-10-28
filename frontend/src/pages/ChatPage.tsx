import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowRight, Bot, Send, Sparkles, User as UserIcon } from "lucide-react";
import { api } from "../api/client";
import type { ChatMessage } from "../api/types";
import Markdown from "../components/Markdown";
import { DemoBadge, Empty, ErrorBox, Loading } from "../components/States";
import { Button } from "../components/ui";
import { navigate, useLoad } from "../hooks";

const STARTERS = [
  "What are Python data types?",
  "How do list comprehensions work?",
  "Explain Python scope (LEGB)",
  "Why can't a list be a dictionary key?",
];

export default function ChatPage() {
  const { data, error, loading, reload, setData } = useLoad(api.chatHistory);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const messages = data?.messages ?? [];
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, sending]);

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || sending || !data) return;
    setSending(true);
    setSendError(null);
    setInput("");
    const optimistic: ChatMessage = {
      id: `local-${Date.now()}`,
      user_id: "",
      subject: "Python Programming",
      role: "user",
      content: message,
      suggested_followups: [],
      is_mock: data.is_mock,
      provider: "",
    };
    setData({ ...data, messages: [...data.messages, optimistic] });
    try {
      const reply = await api.sendChat(message, "Python Programming");
      setData((d) => (d ? { ...d, messages: [...d.messages, reply] } : d));
    } catch (e) {
      setSendError((e as Error).message);
      setInput(message);
      setData((d) => (d ? { ...d, messages: d.messages.filter((m) => m.id !== optimistic.id) } : d));
    } finally {
      setSending(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    send(input);
  };

  if (loading) return <Loading label="Connecting to AI mentor workspace…" />;
  if (error || !data) return <ErrorBox message={error ?? "No data"} onRetry={reload} />;

  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");

  return (
    <div className="page chat-page">
      <header className="page-head">
        <div>
          <div className="eyebrow">AI MENTOR // CONVERSATIONAL WORKSPACE</div>
          <h1>PYTHON LEARNING CHAT</h1>
          <p className="muted">
            Ask any conceptual question or paste code snippets. Your conversation is saved directly to your account.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {data.is_mock && <DemoBadge />}
          <Button variant="outline" size="sm" rightIcon={ArrowRight} onClick={() => navigate("subjects")}>
            Subject Tracks
          </Button>
        </div>
      </header>

      <section className="card chat" style={{ border: "2px solid var(--border-strong)", boxShadow: "var(--shadow-lg)" }}>
        <div className="chat-log" aria-live="polite">
          {messages.length === 0 && (
            <Empty title="Start your AI dialogue">
              <p className="muted small">Select a starter prompt below or enter any programming question.</p>
            </Empty>
          )}

          {messages.map((m) => (
            <div key={m.id} className={`msg msg-${m.role}`}>
              <div className="msg-avatar" aria-hidden>
                {m.role === "user" ? <UserIcon size={16} /> : <Bot size={16} />}
              </div>
              <div className="msg-bubble">
                <span className="sr-only">{m.role === "user" ? "You said:" : "Assistant said:"}</span>
                {m.role === "assistant" ? <Markdown text={m.content} /> : <p style={{ margin: 0 }}>{m.content}</p>}
              </div>
            </div>
          ))}

          {sending && (
            <div className="msg msg-assistant">
              <div className="msg-avatar" aria-hidden>
                <Bot size={16} />
              </div>
              <div className="msg-bubble typing" aria-label="Assistant is reasoning">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Suggested Followups / Starters */}
        <div className="chips" style={{ padding: "0 20px" }}>
          {(lastAssistant?.suggested_followups.length ? lastAssistant.suggested_followups : STARTERS).map((s) => (
            <button key={s} className="chip" onClick={() => send(s)} disabled={sending}>
              <Sparkles size={12} style={{ verticalAlign: "middle", marginRight: 4, color: "var(--color-gold)" }} aria-hidden />
              {s}
            </button>
          ))}
        </div>

        {sendError && <div style={{ padding: "0 20px" }}><ErrorBox message={sendError} /></div>}

        <form className="chat-input" onSubmit={onSubmit}>
          <label htmlFor="chat-msg" className="sr-only">Your question</label>
          <input
            id="chat-msg"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything about Python scope, mutability, decorators, or algorithms…"
            maxLength={2000}
            autoComplete="off"
          />
          <Button
            type="submit"
            variant="primary"
            disabled={sending || !input.trim()}
            aria-label="Send message"
            style={{ padding: "10px 18px" }}
          >
            <Send size={16} aria-hidden />
          </Button>
        </form>
      </section>
    </div>
  );
}
