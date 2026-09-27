"""Evaluate a support ticket with Gemini's structured output.

Setup:
    pip install -r requirements.txt
    export GEMINI_API_KEY=...     # https://aistudio.google.com/apikey

Run as a console script:
    python gemini_app.py

Run as an API (for Bruno):
    python gemini_app.py --serve
    POST http://localhost:5001/evaluate   body: {"ticket": "optional override text"}
"""

import os
import sys
import time
from typing import Literal

from flask import Flask, jsonify, request
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

SAMPLE_TICKET = (
    "Hey, my payment failed twice and my account got locked out. "
    "I need this fixed immediately for a client presentation!"
)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
PORT = int(os.environ.get("GEMINI_PORT", 5001))


class GeminiTicketEvaluation(BaseModel):
    """The three decisions we want out of the ticket, forced into JSON via response_schema."""

    urgency_score: int = Field(ge=1, le=5, description="Urgency from 1 (low) to 5 (critical)")
    routing_target: Literal[
        "billing_support", "technical_support", "account_manager", "general_faq"
    ]
    requires_human_escalation: bool


def evaluate_with_gemini(ticket_text: str) -> dict:
    """Ask Gemini the three questions via a Pydantic response_schema and time the call."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"error": "GEMINI_API_KEY is not set"}

    start = time.perf_counter()
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=(
                "Evaluate this customer support ticket and decide its urgency, "
                f"routing, and whether it needs human escalation:\n\n{ticket_text}"
            ),
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiTicketEvaluation,
            ),
        )
    except Exception as error:  # noqa: BLE001 - surface any provider/network error to the caller
        return {"error": str(error), "latency_ms": (time.perf_counter() - start) * 1000}

    latency_ms = (time.perf_counter() - start) * 1000
    parsed: GeminiTicketEvaluation = response.parsed
    usage = response.usage_metadata

    return {
        "latency_ms": round(latency_ms, 2),
        "model": GEMINI_MODEL,
        "decisions": parsed.model_dump(),
        "usage": {
            "input_tokens": usage.prompt_token_count if usage else None,
            "output_tokens": usage.candidates_token_count if usage else None,
            "total_tokens": usage.total_token_count if usage else None,
        },
    }


def evaluate(ticket_text: str) -> dict:
    return {"ticket": ticket_text, "gemini": evaluate_with_gemini(ticket_text)}


def print_result(result: dict) -> None:
    print(f"\nTicket: {result['ticket']}\n")
    print(f"--- Gemini ({GEMINI_MODEL}) ---")
    print(result["gemini"])
    print()


app = Flask(__name__)


@app.post("/evaluate")
def evaluate_endpoint():
    ticket_text = (request.get_json(silent=True) or {}).get("ticket", SAMPLE_TICKET)
    return jsonify(evaluate(ticket_text))


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        print("Warning: GEMINI_API_KEY is not set - the call will fail.")

    print_result(evaluate(SAMPLE_TICKET))

    if "--serve" in sys.argv:
        print(f"Serving on http://localhost:{PORT} - POST /evaluate with {{\"ticket\": \"...\"}}")
        app.run(port=PORT)
