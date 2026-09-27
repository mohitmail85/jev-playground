# Video Script: What Is Jev, and Why Use It Over an LLM? (~10 min)

Format: talking points to say in your own words, with on-screen cues. Not a
word-for-word teleprompter script — expand naturally as you talk.

---

## [0:00–0:45] Hook + what this video covers

*(Talk to camera)*

- "I'm going to show you a decision engine called Jev, run it side by side
  against Gemini on the exact same task, and explain why — for decisions,
  not writing — it's a different tool entirely, not just a smaller/cheaper
  LLM."
- Roadmap: what Jev is → why it's architecturally different from an LLM →
  live side-by-side demo → what the results actually show → when to use
  which.

---

## [0:45–2:30] What is Jev?

*(Screen: BeatAPI skill doc / TypeSafe AI docs)*

- Jev is TypeSafe AI's model, accessed here through **BeatAPI**, a catalogue
  that exposes it (and social data, web search, image/video models) through
  one API key.
- TypeSafe's own docs call this a **"System One"** model — a nod to Kahneman's
  fast, intuitive "System 1" thinking, as opposed to an LLM generating text
  token by token. The pitch: most product decisions ("is this urgent?",
  "which team handles this?") aren't creative writing tasks — they're fast
  judgment calls, and Jev is purpose-built for exactly that shape of problem.
- You don't prompt it. You ask it **typed questions**, three kinds:
  - **`noul`** — a yes/no question ("does this need human escalation?")
  - **`choice`** — pick one of several labeled options ("which team?")
  - **`score`** — rate against an ordered rubric ("how urgent, 1 to 5?")
- Every answer comes back with a **probability**, not just a label — a `noul`
  gives you "0.74 probability yes," a `choice` gives you a probability for
  *every* option, not just the winner.
- *(Screen: show the raw JSON response from earlier, e.g. `jev-1.13-free`
  answering the escalation question)* — point out `"noul": 0.77` directly in
  the payload.

**Key line to say:** "Notice there's no prompt. I'm not writing 'please
respond only in JSON, do not include any other text.' I'm describing the
question's *shape*, and the shape of the answer is guaranteed."

---

## [2:30–3:30] The experiment setup

*(Screen: project folder — `gemini_app.py`, `jev_app.py`, `bruno/`)*

- Built two tiny, independent apps, each exposing one endpoint:
  `POST /evaluate`.
- Both get asked the **same three questions** about the **same ticket**:
  > "Hey, my payment failed twice and my account got locked out. I need this
  > fixed immediately for a client presentation!"
  1. `urgency_score` — 1 to 5
  2. `routing_target` — `billing_support` / `technical_support` /
     `account_manager` / `general_faq`
  3. `requires_human_escalation` — yes/no
- Gemini's version: same three fields, but defined as a **Pydantic schema**
  passed as `response_schema`, with a plain-English instruction wrapped
  around the ticket text.
- Bruno collection has one request per app, so both can be fired back to
  back and compared directly.

---

## [3:30–4:15] Show the code, side by side

*(Screen: split `gemini_app.py` / `jev_app.py`)*

- Gemini side: a text prompt, a Pydantic model, `response_mime_type:
  application/json`. It's an LLM being *told* to behave like an API.
- Jev side: a dictionary of typed questions. No instructions to "only return
  JSON" — the question type itself *is* the contract.
- Say out loud: "This is the core architectural difference. One is text
  generation constrained after the fact. The other has no unconstrained mode
  to fall back to."

---

## [4:15–5:30] Live demo

*(Screen: Bruno, run "Gemini" request, then "Jev" request)*

- Fire both against the same ticket.
- Show both raw responses on screen.

**Results table (say these numbers out loud as they appear):**

| Field | Gemini | Jev |
|---|---|---|
| `urgency_score` | 5 | 4.96 (confidence 0.96) |
| `routing_target` | billing_support | billing_support (confidence 1.0) |
| `requires_human_escalation` | true | true (probability 0.74) |
| Latency | 2149 ms | 438 ms |
| Tokens | 44 in / 29 out | 503 in / 89 out |

- Call out: "Same three answers. Both correct. Now look at everything else."

---

## [5:30–7:00] What the numbers actually mean

- **Speed:** Jev answered in about a fifth of the time. It's not generating
  prose and parsing it back into JSON — it's answering a typed question
  directly.
- **Confidence, natively:** Jev's `billing_support` call came back at
  confidence 1.0 — full certainty. Gemini gave the same label with *zero*
  visibility into how sure it was. If Jev had come back at, say, 0.55
  confidence, that's a signal to route the ticket to a human for review
  instead of trusting it blindly. Gemini structurally cannot give you that
  signal — a schema only tells you the *shape* of the answer, never how sure
  the model is.
- **Tokens are a different currency here:** Jev used more tokens (503 in) but
  it's on the **free tier** — input and output cost $0 even at zero balance.
  Gemini's tokens are billed per call. Point isn't "cheaper," it's "the
  pricing model matches the task" — a decision engine, priced for high-volume
  small decisions.

---

## [7:00–8:15] The reliability incident (real, not staged)

*(Screen: the 503 error we actually hit, and the terminal test that isolated it)*

- While building this, Gemini's **structured-output path** — `response_schema`
  — returned `503 UNAVAILABLE: high demand` repeatedly, on several of
  Gemini's newer flash models.
- Isolated it: a **plain text prompt to the exact same model, at the exact
  same time**, worked fine. Only the JSON-constrained path failed.
- "That's not a fluke, it's the architecture showing itself. Forcing valid
  JSON out of a free-form text generator is a secondary code path —
  constrained decoding bolted onto generation — and it's visibly more
  fragile under load than the model's native mode."
- Had to fall back to an older model (`gemini-3.1-flash-lite`) to get
  reliable structured output. Jev never had this problem, because typed
  answers are the *only* thing it produces — there's no more-reliable
  fallback mode it's failing to use, because it never left that mode.

---

## [8:15–9:15] So — how is Jev different from *any* LLM, not just Gemini?

*(Talk to camera, no screen needed — this is the generalizing/explainer beat)*

- Every general-purpose LLM — Gemini, GPT, Claude, doesn't matter — is
  fundamentally a **text generator**. Structured output, function calling,
  JSON mode: all of it is a layer of constraints wrapped around "predict the
  next token," enforced after training, at inference time.
- Jev inverts that: the typed question **is** the interface. You're not
  hoping the model follows instructions to format its answer — the answer's
  shape (a score, a choice, a yes/no) is guaranteed by what you asked for, and
  it comes with a calibrated probability because that's what the model was
  built to output, not squeezed into producing.
- Practical consequence: no prompt engineering. You don't iterate on wording
  to stop the model from adding a caveat sentence before the JSON, or
  wrapping it in markdown fences. You describe the decision; you get the
  decision.

---

## [9:15–10:00] When to use which — and wrap-up

- Be fair on camera: Gemini is general-purpose. It can also draft the reply
  email, summarize the whole conversation, or answer something you didn't
  anticipate. Jev can't — it only answers the typed questions you give it.
- The line: **is this task a decision, or is it generation?** Urgency,
  routing, approve/deny, escalate/don't — that's decisions: use Jev. Drafting
  text, summarizing, open-ended reasoning: that's generation: use an LLM.
- Close: "Same ticket, same three answers, a fifth of the latency, and a real
  confidence score instead of a label with no idea how sure the model was.
  For the decision slice of your product, that's the difference between
  guessing with extra steps and an actual measurement."

*(End card: links to BeatAPI, the repo/Bruno collection)*

---

## Appendix: quick-reference numbers for on-screen graphics

- Ticket: "Hey, my payment failed twice and my account got locked out. I need
  this fixed immediately for a client presentation!"
- Gemini model used: `gemini-3.1-flash-lite` (had to swap from
  `gemini-3.8-flash` due to 503s on the structured-output path)
- Jev model used: `jev-1.13-free` (BeatAPI, free tier, 1 req/min rate limit
  pre-credit)
- Full result JSON and the 503 reproduction steps are in this session's
  history / `EXPERIMENT.md` if you want to pull exact quotes on screen.
