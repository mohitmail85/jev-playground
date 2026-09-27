# jev-playground

A head-to-head experiment: **Jev** (a purpose-built decision model, via
[BeatAPI](https://beatapi.io)'s free `jev-1.13-free`) vs. **Gemini**
(`gemini-3.1-flash-lite`, a general-purpose LLM forced into JSON via a
Pydantic `response_schema`) — both answering the exact same three questions
about the exact same support ticket, so you can compare speed, output shape,
and confidence side by side.

See [`EXPERIMENT.md`](EXPERIMENT.md) for the full write-up of what we ran and
what came back, and [`VIDEO_SCRIPT.md`](VIDEO_SCRIPT.md) for a ~10-minute
video script walking through it.

## The question

Given a ticket like:

> "Hey, my payment failed twice and my account got locked out. I need this
> fixed immediately for a client presentation!"

Both models are asked:

1. `urgency_score` — how urgent, 1 (low) to 5 (critical)?
2. `routing_target` — `billing_support`, `technical_support`,
   `account_manager`, or `general_faq`?
3. `requires_human_escalation` — does a human need to step in?

## Project layout

```
gemini_app.py       Flask app, POST /evaluate → asks Gemini via response_schema
jev_app.py           Flask app, POST /evaluate → asks Jev via BeatAPI's typed questions
requirements.txt     Shared dependencies for both apps
bruno/               Bruno collection: one request per app, same ticket
EXPERIMENT.md         Write-up of the comparison and results
VIDEO_SCRIPT.md       ~10-minute script for a walkthrough video
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file (gitignored) with:

```
GEMINI_API_KEY=...     # https://aistudio.google.com/apikey
BEATAPI_API_KEY=...    # https://beatapi.io/dashboard/apikeys
```

## Running

Each app runs standalone, on its own port, and can be tested as a console
script or served as an API.

```bash
set -a && source .env && set +a

python3 gemini_app.py            # console: prints one evaluation
python3 gemini_app.py --serve    # API: http://localhost:5001/evaluate

python3 jev_app.py               # console: prints one evaluation
python3 jev_app.py --serve       # API: http://localhost:5002/evaluate
```

Both run at the same time on different ports, so you can call them side by
side — e.g. from the Bruno collection in `bruno/` (open the folder in Bruno,
select the `local` environment, run "Gemini" and "Jev").

### Example request

```bash
curl -X POST http://localhost:5001/evaluate \
  -H 'Content-Type: application/json' \
  -d '{"ticket": "My app keeps crashing on login, please help."}'
```

`ticket` is optional on both endpoints — omit it and you get the sample ticket
above.

## Notes

- `jev-1.13-free` is BeatAPI's free tier: $0 cost, but rate-limited to one
  successful request per minute until the account has credit.
- Gemini's `response_schema` (structured output) path has been flaky under
  load on newer flash models (503 "high demand") even when plain text calls
  to the same model succeed — see `EXPERIMENT.md` for details. We settled on
  `gemini-3.1-flash-lite` as the most reliable model for this.
