import { useRef, useState, type FormEvent } from "react";
import {
  ArrowDown,
  ArrowRight,
  Award,
  Bot,
  BrainCircuit,
  Compass,
  FolderKanban,
  GraduationCap,
  Lock,
  Medal,
  Sparkles,
  Swords,
  Target,
  Trophy,
  Zap,
} from "lucide-react";
import { api } from "../api/client";
import type { User } from "../api/types";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { HeroArtwork } from "../components/ui/HeroArtwork";

const EMAIL_RE = /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/;

export default function AuthPage({
  onAuth,
}: {
  readonly onAuth: (u: User, token: string, isNew: boolean) => void;
}) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [referral, setReferral] = useState(() => new URLSearchParams(window.location.hash.split("?")[1] ?? window.location.search).get("ref") ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const accountRef = useRef<HTMLDivElement>(null);
  const journeyRef = useRef<HTMLElement>(null);
  const philosophyRef = useRef<HTMLElement>(null);
  const arenaRef = useRef<HTMLElement>(null);
  const nameInputRef = useRef<HTMLInputElement>(null);
  const emailInputRef = useRef<HTMLInputElement>(null);

  const validate = () => {
    if (mode === "register" && name.trim().length < 2) {
      return "Please enter your full name (at least 2 characters).";
    }
    if (!EMAIL_RE.test(email.trim())) {
      return "Please enter a valid academic or personal email address.";
    }
    if (mode === "register" && password.length < 6) {
      return "Password must be at least 6 characters.";
    }
    if (!password) {
      return "Please enter your password.";
    }
    return null;
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = validate();
    if (problem) return setError(problem);
    setBusy(true);
    setError(null);
    try {
      const res =
        mode === "register"
          ? await api.register(name.trim(), email.trim(), password, referral.trim() || undefined)
          : await api.login(email.trim(), password);
      onAuth(res.user, res.token, mode === "register");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const switchMode = (m: "login" | "register") => {
    setMode(m);
    setError(null);
    setTimeout(() => {
      if (m === "register") {
        nameInputRef.current?.focus();
      } else {
        emailInputRef.current?.focus();
      }
    }, 50);
  };

  const focusAuth = (preferredMode: "login" | "register" = "register") => {
    switchMode(preferredMode);
    accountRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const scrollToPhilosophy = () => {
    philosophyRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const scrollToJourney = () => {
    journeyRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const scrollToArena = () => {
    arenaRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <div className="landing-shell">
      {/* Editorial Brutalist Top Marquee */}
      <div className="landing-ticker" aria-hidden="true">
        <span>/// PRAGYAX EDTECH ARENA — NEXT-GEN AI GAMIFIED MASTERY — 1v1 CODE BATTLES — ADAPTIVE DIAGNOSTICS — VERIFIED SCORECARDS — REAL PORTFOLIO EVIDENCE ///</span>
      </div>

      {/* Subtle Architectural Grid Lines Overlay */}
      <div className="grid-lines-bg" aria-hidden="true" />

      {/* Top Editorial Navigation */}
      <header className="landing-nav">
        <a href="#/" className="brand">
          <GraduationCap size={24} aria-hidden /> Pragya<span className="brand-x">X</span>
        </a>

        <nav className="landing-nav-links" aria-label="Landing Navigation">
          <a href="#philosophy" onClick={(e) => { e.preventDefault(); scrollToPhilosophy(); }}>
            Philosophy
          </a>
          <a href="#arena" onClick={(e) => { e.preventDefault(); scrollToArena(); }}>
            Arena & Battles
          </a>
          <a href="#journey" onClick={(e) => { e.preventDefault(); scrollToJourney(); }}>
            Journey
          </a>
          <a href="#capabilities">Capabilities</a>
          <button
            type="button"
            className="nav-text-btn"
            onClick={() => focusAuth("login")}
          >
            Sign in
          </button>
        </nav>

        <div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => focusAuth("register")}
          >
            Get Started
          </Button>
        </div>
      </header>

      {/* Hero Section — Editorial Brutalist Typography & Asymmetric Layout */}
      <section className="hero-section" id="hero">
        <div className="hero-text-block">
          <div className="eyebrow">AI-POWERED GAMIFIED LEARNING ARENA</div>

          <h1 className="hero-headline">
            LEARN.<br />
            COMPETE.<br />
            <em>EVOLVE.</em>
          </h1>

          <p className="hero-lead">
            Your AI-powered learning arena. Master concepts, test your skills,
            compete with others, and turn knowledge into real-world achievements.
          </p>

          {/* Authentication Card Positioned Directly in Upper Viewport */}
          <div className="auth-card hero-auth-card" ref={accountRef} id="account">
            <div className="tabs" role="tablist" aria-label="Account Mode">
              <button
                type="button"
                role="tab"
                aria-selected={mode === "register"}
                className={mode === "register" ? "tab active" : "tab"}
                onClick={() => switchMode("register")}
              >
                Create account
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "login"}
                className={mode === "login" ? "tab active" : "tab"}
                onClick={() => switchMode("login")}
              >
                Log in
              </button>
            </div>

            <form onSubmit={submit} noValidate>
              {mode === "register" && (
                <label className="field">
                  <span>Full name</span>
                  <input
                    ref={nameInputRef}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    placeholder="e.g. Asha Sharma"
                  />
                </label>
              )}

              <label className="field">
                <span>Email address</span>
                <input
                  ref={emailInputRef}
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="you@college.edu"
                />
              </label>

              <label className="field">
                <span>Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                  placeholder={mode === "register" ? "At least 6 characters" : "Your password"}
                />
              </label>

              {error && <Alert variant="error" message={error} />}

              {mode === "register" && (
                <label className="field">
                  <span>Referral code (optional)</span>
                  <input
                    value={referral}
                    maxLength={64}
                    onChange={(e) => setReferral(e.target.value.toUpperCase())}
                    placeholder="e.g. PRAGYAX-CODE"
                  />
                </label>
              )}

              <Button
                type="submit"
                variant="primary"
                block
                disabled={busy}
                loading={busy}
                style={{ marginTop: 8 }}
              >
                {mode === "register" ? "Enter the Arena & Start Learning" : "Log In to Your Arena Account"}
              </Button>
            </form>

            <div className="auth-card-footer">
              <span className="fine">
                <Lock size={12} aria-hidden /> Session restored automatically
              </span>
              <button
                type="button"
                className="scroll-peek-link"
                onClick={scrollToJourney}
              >
                Explore curriculum & arena <ArrowDown size={13} aria-hidden />
              </button>
            </div>
          </div>
        </div>

        {/* Sculptural Knowledge Metaphor Artwork Column */}
        <div className="hero-artwork-column">
          <HeroArtwork />

          {/* Core Foundation Highlights Aligned Below Artwork */}
          <div className="hero-meta-points">
            <div className="hero-meta-item">
              <strong>01 / Assess</strong>
              <span>5-Question Diagnostics</span>
            </div>
            <div className="hero-meta-item">
              <strong>02 / Arena</strong>
              <span>1v1 Real-Time Battles</span>
            </div>
            <div className="hero-meta-item">
              <strong>03 / Prove</strong>
              <span>Verified Skill Scorecards</span>
            </div>
          </div>
        </div>
      </section>

      {/* Section A: Learning Philosophy */}
      <section id="philosophy" ref={philosophyRef} className="editorial-section">
        <div className="section-header">
          <div className="eyebrow">THE PRAGYAX METHOD</div>
          <h2>FROM THEORY TO PRACTICE. PROVEN BY CODE.</h2>
          <p className="muted">
            College learning shouldn't stop at reading textbooks. PragyaX combines
            interactive dialogue, objective testing, and real coding practice.
          </p>
        </div>

        <div className="philosophy-grid">
          <article className="philosophy-card">
            <span className="philosophy-num">PHASE // 01</span>
            <div className="capability-icon">
              <Compass size={22} aria-hidden />
            </div>
            <h3 className="philosophy-title">DISCOVER</h3>
            <p className="philosophy-desc">
              Understand what you already know. Estimate your starting point and
              knowledge boundaries with rapid diagnostic challenges.
            </p>
          </article>

          <article className="philosophy-card">
            <span className="philosophy-num">PHASE // 02</span>
            <div className="capability-icon">
              <Sparkles size={22} aria-hidden />
            </div>
            <h3 className="philosophy-title">PRACTICE</h3>
            <p className="philosophy-desc">
              Build knowledge through conversational AI tutoring, contextual follow-ups,
              and bite-sized daily code breaker puzzles.
            </p>
          </article>

          <article className="philosophy-card">
            <span className="philosophy-num">PHASE // 03</span>
            <div className="capability-icon">
              <Trophy size={22} aria-hidden />
            </div>
            <h3 className="philosophy-title">PROVE</h3>
            <p className="philosophy-desc">
              Demonstrate genuine progress. Server-evaluated assessments award verified
              proficiency ratings, points, and unlockable achievement badges.
            </p>
          </article>
        </div>
      </section>

      {/* Section Arena: 1v1 Battles & Competitions */}
      <section id="arena" ref={arenaRef} className="editorial-section">
        <div className="section-header">
          <div className="eyebrow">YOUR ARENA. YOUR ARENA RANKING.</div>
          <h2>COMPETE HEAD-TO-HEAD IN 1v1 BATTLES</h2>
          <p className="muted">
            Test your speed, accuracy, and depth against peers in synchronized duels. Earn XP, maintain streaks, and climb the global leaderboards.
          </p>
        </div>

        <div className="grid-3">
          <div className="card">
            <div className="capability-icon" style={{ backgroundColor: "var(--color-purple)", color: "#FFFFFF" }}>
              <Swords size={22} aria-hidden />
            </div>
            <h3 style={{ marginTop: 14 }}>1v1 Live Duels</h3>
            <p className="muted small">
              Challenge any peer via email invite. Both face identical timed questions evaluated server-side.
            </p>
            <div style={{ marginTop: 8 }}>
              <span className="badge badge-accent">Synchronous Grading</span>
            </div>
          </div>

          <div className="card">
            <div className="capability-icon">
              <Trophy size={22} aria-hidden />
            </div>
            <h3 style={{ marginTop: 14 }}>Hosted Tournaments</h3>
            <p className="muted small">
              Join college-wide, company-sponsored, and student-run competitions with scheduled windows and real prizes.
            </p>
            <div style={{ marginTop: 8 }}>
              <span className="badge badge-primary">Ranked Contests</span>
            </div>
          </div>

          <div className="card">
            <div className="capability-icon" style={{ backgroundColor: "var(--color-plum-dark)", color: "var(--color-gold)" }}>
              <Medal size={22} aria-hidden />
            </div>
            <h3 style={{ marginTop: 14 }}>Global Leaderboards</h3>
            <p className="muted small">
              Transparent standings for assessment mastery, daily challenge streaks, battle wins, and verified achievements.
            </p>
            <div style={{ marginTop: 8 }}>
              <span className="badge">Zero Fake Metrics</span>
            </div>
          </div>
        </div>
      </section>

      {/* Section B: The Learning Journey */}
      <section id="journey" ref={journeyRef} className="editorial-section">
        <div className="section-header">
          <div className="eyebrow">STEP-BY-STEP PROGRESSION</div>
          <h2>THE JOURNEY: FROM THEORY TO PRACTICAL SKILL.</h2>
          <p className="muted">
            Each learning cycle takes you from concept exploration to objective evaluation.
          </p>
        </div>

        <div className="journey-sequence">
          <div className="journey-step active">
            <span className="journey-step-badge">1</span>
            <h3>Subject Selection</h3>
            <p>
              Choose from specialized curriculum tracks: Python, AI/ML, Biology, and Business.
            </p>
          </div>

          <div className="journey-step">
            <span className="journey-step-badge">2</span>
            <h3>Server Assessment</h3>
            <p>
              Complete a focused 5-question evaluation graded by server-side logic with instant feedback.
            </p>
          </div>

          <div className="journey-step">
            <span className="journey-step-badge">3</span>
            <h3>Personalized Chat</h3>
            <p>
              Deep-dive into weak areas. Ask the learning assistant questions with curated follow-up prompts.
            </p>
          </div>

          <div className="journey-step">
            <span className="journey-step-badge">4</span>
            <h3>Skill Progress</h3>
            <p>
              Review your score percentage, unlock achievements, and climb from Beginner to Advanced mastery.
            </p>
          </div>
        </div>
      </section>

      {/* Section C: Product Capabilities */}
      <section id="capabilities" className="editorial-section">
        <div className="section-header">
          <div className="eyebrow">PLATFORM CAPABILITIES</div>
          <h2>EVERYTHING YOU NEED TO MASTER PRACTICAL SKILLS.</h2>
        </div>

        <div className="capabilities-grid">
          <div className="capability-card">
            <div className="capability-icon">
              <Target size={20} aria-hidden />
            </div>
            <h3>Adaptive Assessments</h3>
            <p>
              Server-evaluated assessments test core conceptual mechanics including
              Python scope (LEGB), mutability, and list comprehensions.
            </p>
          </div>

          <div className="capability-card">
            <div className="capability-icon">
              <Bot size={20} aria-hidden />
            </div>
            <h3>AI Learning Assistant</h3>
            <p>
              Context-aware learning chat with safe Markdown code rendering, intelligent
              suggested follow-ups, and session persistence.
            </p>
          </div>

          <div className="capability-card">
            <div className="capability-icon">
              <BrainCircuit size={20} aria-hidden />
            </div>
            <h3>Diagnostic Roadmaps</h3>
            <p>
              Targeted topic recommendations derived dynamically from the questions
              you missed during assessments.
            </p>
          </div>

          <div className="capability-card">
            <div className="capability-icon">
              <Zap size={20} aria-hidden />
            </div>
            <h3>Daily Code Breaker</h3>
            <p>
              Solve a daily bite-sized code snippet puzzle to earn instant bonus
              points and maintain your learning streak.
            </p>
          </div>

          <div className="capability-card">
            <div className="capability-icon">
              <FolderKanban size={20} aria-hidden />
            </div>
            <h3>Portfolio Projects</h3>
            <p>
              Build practical projects graded against clear rubrics with milestone tracking and evidence submission links.
            </p>
          </div>

          <div className="capability-card">
            <div className="capability-icon">
              <Award size={20} aria-hidden />
            </div>
            <h3>Verifiable Credentials</h3>
            <p>
              Earn public cryptographic-style verification IDs and certificates that employers or colleges can independently verify.
            </p>
          </div>
        </div>
      </section>

      {/* Section D: Bottom Closing Section with Quick Action to Return to Form */}
      <section className="landing-closing-banner">
        <div className="closing-banner-inner">
          <div className="eyebrow">READY TO PROVE YOUR SKILLS?</div>
          <h2>BEGIN YOUR ARENA JOURNEY TODAY.</h2>
          <p className="muted">
            Free diagnostic evaluation, real-time AI tutor dialogues, and verified badges.
          </p>
          <div style={{ marginTop: 24 }}>
            <Button
              variant="primary"
              size="lg"
              onClick={() => focusAuth("register")}
              rightIcon={ArrowRight}
            >
              Start Learning Now
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
