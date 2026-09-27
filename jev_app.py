"""Evaluate a support ticket with BeatAPI's free JEV decision model.

Setup:
    pip install -r requirements.txt
    export BEATAPI_API_KEY=...   # https://beatapi.io/dashboard/apikeys

Run as a console script:
    python jev_app.py

Run as an API (for Bruno):
    python jev_app.py --serve
    POST http://localhost:5002/evaluate   body: {"ticket": "optional override text"}

Note: the free model (jev-1.13-free) is rate-limited to one successful
request per minute until the BeatAPI account has credit.
"""

import os
import sys
import time

import requests
from flask import Flask, jsonify, request

SAMPLE_TICKET = (
    "Hey, my payment failed twice and my account got locked out. "
    "I need this fixed immediately for a client presentation!"
)

JEV_MODEL = os.environ.get("JEV_MODEL", "jev-1.13-free")
BEATAPI_RUN_URL = "https://api.beatapi.io/v1/capabilities/run"
PORT = int(os.environ.get("JEV_PORT", 5002))

URGENCY_LEVELS = [
    "Low priority; no immediate action needed",
    "Minor issue; can wait a few days",
    "Moderate issue; should be addressed within a day",
    "High priority; needs attention soon",
    "Critical; requires immediate action",
]

ROUTING_CRITERIA = {
    "billing_support": "Issues about payments, charges, refunds, or billing account status",
    "technical_support": "Technical bugs, errors, or product malfunctions",
    "account_manager": "Escalations needing dedicated account management or high-value client handling",
    "general_faq": "General questions answerable via standard documentation",
}


def evaluate_with_jev(ticket_text: str) -> dict:
    """Ask BeatAPI's free JEV model the three questions and time the call."""
    api_key = os.environ.get("BEATAPI_API_KEY")
    if not api_key:
        return {"error": "BEATAPI_API_KEY is not set"}

    payload = {
        "reference": f"model:{JEV_MODEL}",
        "input": {
            "state": ticket_text,
            "questions": {
                "urgency_score": {
                    "type": "score",
                    "instructions": "How urgent is this support ticket?",
                    "criteria": URGENCY_LEVELS,
                },
                "routing_target": {
                    "type": "choice",
                    "instructions": "Which team should handle this ticket?",
                    "criteria": ROUTING_CRITERIA,
                },
                "requires_human_escalation": {
                    "type": "noul",
                    "instructions": (
                        "Does this ticket require escalation to a human support agent "
                        "rather than being resolved by automation?"
                    ),
                },
            },
        },
    }

    start = time.perf_counter()
    try:
        response = requests.post(
            BEATAPI_RUN_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        return {"error": str(error), "latency_ms": (time.perf_counter() - start) * 1000}

    latency_ms = (time.perf_counter() - start) * 1000
    answers = data["answers"]
    urgency = answers["urgency_score"]
    routing = answers["routing_target"]
    escalation = answers["requires_human_escalation"]

    return {
        "latency_ms": round(latency_ms, 2),
        "model": data.get("model", JEV_MODEL),
        "decisions": {
            "urgency_score": round(urgency["score"] + 1, 2),  # API scores from 0; shift to 1-5
            "routing_target": routing["choice"],
            "requires_human_escalation": escalation["noul"] > 0.5,
        },
        "confidence": {
            "urgency_score": urgency["confidence"],
            "routing_target": routing["confidence"],
            "requires_human_escalation": escalation["noul"],
        },
        "probabilities": {
            "urgency_score": urgency["probabilities"],
            "routing_target": routing["probabilities"],
        },
        "usage": data.get("usage"),
    }


def evaluate(ticket_text: str) -> dict:
    return {"ticket": ticket_text, "jev": evaluate_with_jev(ticket_text)}


def print_result(result: dict) -> None:
    print(f"\nTicket: {result['ticket']}\n")
    print(f"--- Jev ({JEV_MODEL}) ---")
    print(result["jev"])
    print()


app = Flask(__name__)


@app.post("/evaluate")
def evaluate_endpoint():
    ticket_text = (request.get_json(silent=True) or {}).get("ticket", SAMPLE_TICKET)
    return jsonify(evaluate(ticket_text))


if __name__ == "__main__":
    if not os.environ.get("BEATAPI_API_KEY"):
        print("Warning: BEATAPI_API_KEY is not set - the call will fail.")

    print_result(evaluate(SAMPLE_TICKET))

    if "--serve" in sys.argv:
        print(f"Serving on http://localhost:{PORT} - POST /evaluate with {{\"ticket\": \"...\"}}")
        app.run(port=PORT)
