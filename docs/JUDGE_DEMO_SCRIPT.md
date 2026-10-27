# PragyaX Judge Demonstration Script (5-Minute Master Walkthrough)

**Audience:** Hackathon Technical Judges & Product Evaluators  
**Total Duration:** Exactly 5 Minutes  
**Prerequisites:** 
- Backend running at `http://127.0.0.1:8011`
- Frontend running at `http://127.0.0.1:5174`
- PostgreSQL active on `127.0.0.1:55433`

---

## Demo Timeline Overview

```
0:00 ── 1:00  [Act 1: The Active Learner] ── Diagnostic, Personalized Roadmap, Real XP
1:00 ── 2:15  [Act 2: The 1v1 Battle Arena] ── Real-Time Competition & Server Scoring
2:15 ── 3:15  [Act 3: Practical Projects] ── Multi-Milestone Capstone & Portfolio
3:15 ── 4:15  [Act 4: Collegiate Championship] ── Host Org, Leaderboards & Certificates
4:15 ── 5:00  [Act 5: Cryptographic Trust] ── Zero-Auth Public Verification & Architecture
```

---

## Act 1: The Active Learner (0:00 – 1:00)

### Action & Screen:
1. Open browser to `http://127.0.0.1:5174`.
2. Register a new user:
   - **Name:** `Aarav Sharma`
   - **Email:** `aarav.demo@pragyax.edu`
   - **Password:** `DemoPassword123!`
3. Show the **Guided Landing**: Notice how the application immediately prompts to start in the Learning Hub. Point out the badge in the lower sidebar: **"Demo AI Mode"** (indicating offline deterministic resilience).
4. Select **Python Mastery**. Click **Take Initial Diagnostic**.
5. Complete 5 diagnostic questions. Submit.

### Talking Points:
> *"Most platforms teach coding by making you watch 40 hours of passive video tutorials. PragyaX does the opposite. We immediately assess your actual baseline. Behind the scenes, the server calculates your knowledge level, isolates your specific weaknesses, and automatically generates an adaptive learning roadmap tailored just for you."*

---

## Act 2: The 1v1 Battle Arena (1:00 – 2:15)

### Action & Screen:
1. Open an incognito window alongside the main window.
2. In incognito, register a second student: `Priya Patel` (`priya.demo@pragyax.edu`).
3. In Aarav's window, navigate to **1v1 Battles** (`#/battles`).
4. In the "Challenge a student" card, enter `priya.demo@pragyax.edu` and click **Send Invitation**.
5. Switch to Priya's window. Watch the notification badge increment to `1` in real time.
6. Open Priya's **1v1 Battles** page: Priya sees Aarav's pending invitation. Click **Accept**.
7. Both players are immediately placed in the synchronized **Battle Lobby**.
8. Both players click **"I'm ready"**. The status transitions immediately to **ACTIVE**.
9. Show the synchronized anti-tamper countdown timer. Answer the 5 questions in both windows and submit.
10. Watch the battle status instantly change to **COMPLETED**:
    - Winner declared with exact score breakdown.
    - Server delivers question-by-question review with explanations.
    - Click **"See achievements"** to see instant XP and badge awards.

### Talking Points:
> *"Peer motivation drives retention. PragyaX includes a synchronous 1v1 battle arena. Notice that answer keys are NEVER sent to the client browser until both players have locked in their submissions, completely eliminating DevTools cheating. The battle resolves atomically in PostgreSQL using transaction advisory locks."*

---

## Act 3: Practical Projects & Portfolio (2:15 – 3:15)

### Action & Screen:
1. In Aarav's window, navigate to **Projects** (`#/projects`).
2. Show the multi-tier curated projects: *Basic*, *Intermediate*, *Advanced*, *Extreme*.
3. Expand **CLI Expense Tracker** (Basic Python Project).
4. Check off the 3 milestones:
   - [x] Set up project repo and structured SQLite / JSON storage
   - [x] Implement CLI command parser for adding and listing expenses
   - [x] Add monthly budget summary and category filtering
5. Enter evidence:
   - **Reflection:** *"Built a clean CLI expense tracker using Python dataclasses and argparse with thorough automated tests."*
   - **Link:** `https://github.com/aarav/expense-tracker-cli`
   - **Rubric:** Rate 3/3 on Code Quality, Architecture, and Error Handling.
6. Click **Save project submission**.
7. Navigate to **Skill Profile** (`#/profile`):
   - Show the newly recorded project under **Projects** marked with a distinct **"self-assessed"** badge.

### Talking Points:
> *"We believe in honest credentialing. Anyone can claim they built a project. PragyaX stores the milestones, the student's self-reflection, and their rubric evaluation directly in their skill profile, clearly disclaimed as self-assessed evidence until peer-reviewed or employer-verified."*

---

## Act 4: Collegiate Championship & Live Leaderboard (3:15 – 4:15)

### Action & Screen:
1. Navigate to **Competitions** (`#/competitions`).
2. Show the registered host organizations: Point out student clubs, engineering colleges, and company sponsors.
3. Open **National Python Championship 2026**.
4. Show the timed challenge window, eligibility rules, and live leaderboard.
5. Demonstrate the organizer controls: Click **Announce Winners**.
6. The system computes the top contestant, marks the competition completed, issues an official verified champion certificate, and delivers an in-app achievement notification.

### Talking Points:
> *"Colleges and companies can host branded competitive challenges directly on PragyaX. Timed entries prevent late submissions, answer keys remain hidden on the server, and the winner is automatically awarded a cryptographically signed credential upon completion."*

---

## Act 5: Cryptographic Trust & Architecture (4:15 – 5:00)

### Action & Screen:
1. Open a new, completely logged-out private window.
2. Navigate directly to the public verification URL:
   `http://127.0.0.1:5174/#/verify/PRAGYA-CERT-2026-715AE3D7`
3. Show the **Public Verification Screen**:
   - Distinct green badge: **"Signature Verified"**.
   - Displays recipient name, title, issued timestamp, and tamper-evident HMAC-SHA256 signature.
   - Shows platform legal disclaimer: *"Issued by PragyaX as a platform achievement record. Not an accredited qualification."*
4. Click **View / Print**: Show the clean, printable HTML certificate diploma suitable for framing or LinkedIn export.
5. Conclude by showing the terminal evidence: **714 backend tests passing, 0 failed, 100% PostgreSQL persistence with zero SQLite fallbacks.**

### Closing Summary:
> *"PragyaX isn't a mock-up or a fragile prototype. It is a fully operational, test-hardened, PostgreSQL-native learning engine with 714 automated tests passing. We move students from passive theory to verifiable practical mastery."*
