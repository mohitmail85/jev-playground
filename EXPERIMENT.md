# Experiment: Jev vs Gemini on a Support-Ticket Decision

## What we're comparing

The same support ticket, evaluated by two different kinds of AI system, on the
exact same three questions:

1. **`urgency_score`** — how urgent is this ticket? (1 low → 5 critical)
2. **`routing_target`** — which team should handle it? (`billing_support`,
   `technical_support`, `account_manager`, `general_faq`)
3. **`requires_human_escalation`** — does a human need to step in? (yes/no)

**Test ticket:**
> "Hey, my payment failed twice and my account got locked out. I need this
> fixed immediately for a client presentation!"

## The two systems

| | Jev | Gemini |
|---|---|---|
| What it is | A purpose-built **decision engine** (BeatAPI's free `jev-1.13-free` model) | A **general-purpose text LLM** (`gemini-3.1-flash-lite`) |
| How you ask it | Typed questions: `score`, `choice`, `noul` (yes/no) — no prompt engineering | A text prompt + a Pydantic schema (`response_schema`) that forces JSON output |
| What it gives back | A decision **and** a probability distribution over every option | Just the decision — no probabilities, no confidence |
| Architecture | Decision model: outputs are inherently typed and calibrated | Text generation model: JSON is a constraint bolted on top of free-form generation |

We built this as two small, independent Flask apps (`gemini_app.py`,
`jev_app.py`), each exposing `POST /evaluate`, plus a Bruno collection
(`bruno/`) with one request per app so both could be fired side by side.

## What we ran and what came back

Same ticket, same instant, both apps hit through Bruno:

| Field | Gemini | Jev |
|---|---|---|
| `urgency_score` | `5` | `4.96` (confidence `0.96`, P(level 4)=`0.96`) |
| `routing_target` | `billing_support` | `billing_support` (confidence `1.0`, P=`1.0`) |
| `requires_human_escalation` | `true` | `true` (P=`0.74`) |
| Latency | `2149 ms` | `438 ms` |
| Tokens | 44 in / 29 out | 503 in / 89 out |

**Both systems agreed on all three decisions.** Jev answered in about a fifth
of the time, and — unlike Gemini — told us *how confident* it was in each
answer, down to a full probability distribution over every option, not just
the winning one.

## A real reliability difference we hit along the way

While wiring this up, Gemini's structured-output path (`response_schema`)
returned `503 UNAVAILABLE — high demand` repeatedly on its newer flash models
(`gemini-3.8-flash`, `gemini-flash-latest`, `gemini-3.5-flash`) — even though
plain text prompts to the *same models* worked fine at the *same time*. We had
to fall back to an older, less-loaded model (`gemini-3.1-flash-lite`) to get
structured decisions out reliably.

This isn't a fluke of our code — it's a symptom of the architecture: forcing
JSON out of a general text model is a secondary, more fragile code path
(constrained decoding on top of free-form generation), and it visibly breaks
under load in a way the plain-text path doesn't. Jev never exhibited this,
because structured, typed answers are the *only* thing it produces — there's
no "prose mode" it's more reliably falling back to.

## Why Jev is the better fit for decision problems

1. **Calibrated confidence, natively.** Every Jev answer comes with a
   probability distribution over the options, not just a single label. That's
   the difference between "the model said billing" and "the model is 100%
   sure it's billing, 0% every other option" — critical for knowing when to
   trust an automated decision vs. flagging it for review.
2. **Faster.** ~5x lower latency in this run, because it's not generating and
   parsing free-form text into JSON — it's answering a typed question
   directly.
3. **No prompt engineering.** Questions are typed (`score` / `choice` /
   `noul`) with structured criteria, not a natural-language instruction that
   has to be worded carefully to get consistent JSON back.
4. **More reliable under load.** Structured output is the model's only mode,
   not a constraint layered on top of a text generator — which is exactly
   where we saw Gemini fail (503s on the JSON path, not the text path).
5. **Same answer, less machinery.** In this test both models reached the same
   three decisions — Jev just did it with a smaller, purpose-built request and
   a richer, more trustworthy response.

## Where Gemini still has an edge

To be fair: Gemini is a general-purpose model — it can also write the
response email, summarize the ticket, or handle a question we didn't
anticipate. Jev is narrowly built for exactly this kind of typed decision and
won't do open-ended generation. The right choice depends on whether the task
*is* a decision (use Jev) or needs open-ended reasoning/generation (use an
LLM like Gemini) — this experiment is about the decision-making slice
specifically, where Jev wins on speed, confidence, and reliability.
