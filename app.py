"""
app.py
------
Flask web server for StadiumGenie. Exposes:
  GET  /                       -> fan chat UI
  GET  /ops                    -> staff operations dashboard UI
  POST /api/chat                -> fan-facing AI chat
  POST /api/ops/chat            -> staff-facing AI chat (crowd density + incidents)
  POST /api/ops/incidents       -> log a new incident
  GET  /api/ops/incidents       -> list incidents
  POST /api/ops/incidents/<id>/resolve
  GET  /api/emergency-exit/<gate_code>
  GET  /api/health

Security notes:
  - API key is only ever read from the environment, never from the client.
  - All inbound JSON is validated/typed before use.
  - MAX_CONTENT_LENGTH caps request body size at the WSGI layer (defense
    against oversized payload DoS), independent of application-level
    message-length checks.
  - A thread-safe in-memory rate limiter (protected by a lock) guards the
    (costly) AI endpoints from abuse. For multi-process production
    deployment, swap for Flask-Limiter + Redis (noted in README).
  - Every response carries standard security headers (X-Content-Type-Options,
    X-Frame-Options, Referrer-Policy, a restrictive Content-Security-Policy).
  - Flask's Jinja autoescaping protects templated HTML from XSS; free-text
    input is additionally sanitized before it reaches the model.
  - Client identification for rate limiting prefers X-Forwarded-For (Vercel
    sits behind a proxy, so request.remote_addr is otherwise the proxy's IP,
    not the real client's — which would make every visitor share one bucket).
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

from ai_assistant import get_ai_response, sanitize_user_message
from exceptions import AIServiceError, InvalidInputError, NotFoundError, RateLimitExceededError
from stadium_data import (
    build_context_snapshot,
    build_ops_context_snapshot,
    emergency_exit_for_gate,
    list_incidents,
    log_incident,
    resolve_incident,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stadium_genie")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024  # 16 KB request body cap

VALID_INCIDENT_CATEGORIES = {"crowd_surge", "medical", "security", "facility", "other"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}

# --- thread-safe in-memory rate limiter (per client IP) ---------------------
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 20
_request_log: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = Lock()


def get_client_id() -> str:
    """
    Best-effort client identifier for rate limiting.

    Vercel (and most PaaS providers) terminate TLS at a proxy, so
    request.remote_addr reflects the proxy's IP, not the visitor's — every
    user would otherwise share a single rate-limit bucket. X-Forwarded-For
    is set by Vercel's edge network and is trusted in this deployment
    context; if self-hosting behind a different/untrusted proxy, validate
    the proxy chain before trusting this header.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def check_rate_limit(client_id: str) -> None:
    """Raises RateLimitExceededError if the client has exceeded the window quota."""
    now = time.time()
    with _rate_lock:
        q = _request_log[client_id]
        while q and now - q[0] > RATE_LIMIT_WINDOW_SECONDS:
            q.popleft()
        if len(q) >= RATE_LIMIT_MAX_REQUESTS:
            raise RateLimitExceededError("Too many requests. Please wait a moment and try again.")
        q.append(now)


def parse_bool_flag(value: Any, field_name: str) -> bool:
    """
    Strictly validate a boolean-ish JSON field instead of silently coercing
    with bool(value) — bool("false") is True in Python, which would let a
    client send the string "false" and have it treated as truthy.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    raise InvalidInputError(f"{field_name} must be a boolean")


# --- global middleware -------------------------------------------------------
@app.after_request
def set_security_headers(response: Response) -> Response:
    """Attach standard hardening headers to every response."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer-strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'"
    )
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


# --- error handling -----------------------------------------------------------
@app.errorhandler(InvalidInputError)
def handle_invalid_input(e: InvalidInputError):
    return jsonify(error=str(e)), 400


@app.errorhandler(RateLimitExceededError)
def handle_rate_limit(e: RateLimitExceededError):
    response = jsonify(error=str(e))
    response.headers["Retry-After"] = str(RATE_LIMIT_WINDOW_SECONDS)
    return response, 429


@app.errorhandler(AIServiceError)
def handle_ai_error(e: AIServiceError):
    # Log the real cause server-side only; the user-facing message (str(e))
    # is already generic and safe to return as-is.
    logger.warning("AI service error: %s", e.__cause__ or e)
    return jsonify(error=str(e)), 503


@app.errorhandler(NotFoundError)
def handle_not_found(e: NotFoundError):
    return jsonify(error=str(e)), 404


@app.errorhandler(413)
def handle_payload_too_large(e):
    return jsonify(error="Request too large."), 413


@app.errorhandler(500)
def handle_internal_error(e):
    # Catch-all so an unexpected exception never leaks a stack trace or
    # internal detail to the client, even if a future code path forgets
    # to raise one of the typed exceptions above.
    logger.exception("Unhandled server error")
    return jsonify(error="An unexpected error occurred."), 500


# --- pages ---------------------------------------------------------------
@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/ops")
def ops_dashboard() -> str:
    return render_template("ops.html")


@app.route("/api/health")
def health() -> Response:
    return jsonify(status="ok")


# --- fan-facing API --------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
def chat() -> Response:
    check_rate_limit(get_client_id())

    data = request.get_json(silent=True) or {}
    raw_message = data.get("message", "")
    section = data.get("section")
    accessibility = parse_bool_flag(data.get("accessibility"), "accessibility")

    if section is not None and not isinstance(section, str):
        raise InvalidInputError("section must be a string")

    clean_message = sanitize_user_message(raw_message)
    context = build_context_snapshot(section_code=section, accessibility_needs=accessibility)
    reply = get_ai_response(clean_message, context, persona="fan")

    return jsonify(reply=reply, context_used=context)


@app.route("/api/emergency-exit/<gate_code>")
def emergency_exit(gate_code: str) -> Response:
    exit_info = emergency_exit_for_gate(gate_code)
    if not exit_info:
        raise NotFoundError("Unknown gate")
    return jsonify(gate=gate_code.upper(), emergency_exit=exit_info)


# --- ops / staff-facing API (tournament operations vertical) ---------------
@app.route("/api/ops/chat", methods=["POST"])
def ops_chat() -> Response:
    check_rate_limit(get_client_id())

    data = request.get_json(silent=True) or {}
    raw_message = data.get("message", "")
    gate = data.get("gate")

    if gate is not None and not isinstance(gate, str):
        raise InvalidInputError("gate must be a string")

    clean_message = sanitize_user_message(raw_message)
    context = build_ops_context_snapshot(gate_code=gate)
    reply = get_ai_response(clean_message, context, persona="ops")

    return jsonify(reply=reply, context_used=context)


@app.route("/api/ops/incidents", methods=["GET"])
def get_incidents() -> Response:
    gate = request.args.get("gate")
    unresolved_only = request.args.get("unresolved_only", "false").lower() == "true"
    incidents = list_incidents(gate=gate, unresolved_only=unresolved_only)
    return jsonify(incidents=[i.__dict__ for i in incidents])


@app.route("/api/ops/incidents", methods=["POST"])
def create_incident() -> tuple[Response, int]:
    data = request.get_json(silent=True) or {}
    gate = data.get("gate", "")
    category = data.get("category", "")
    description = data.get("description", "")
    severity = data.get("severity", "")

    if not isinstance(gate, str) or not gate.strip():
        raise InvalidInputError("gate is required")
    if category not in VALID_INCIDENT_CATEGORIES:
        raise InvalidInputError(f"category must be one of {sorted(VALID_INCIDENT_CATEGORIES)}")
    if severity not in VALID_SEVERITIES:
        raise InvalidInputError(f"severity must be one of {sorted(VALID_SEVERITIES)}")
    clean_description = sanitize_user_message(description, max_len=300)

    incident = log_incident(
        gate=gate, category=category, description=clean_description, severity=severity
    )
    return jsonify(incident=incident.__dict__), 201


@app.route("/api/ops/incidents/<int:incident_id>/resolve", methods=["POST"])
def resolve_incident_route(incident_id: int) -> Response:
    if not resolve_incident(incident_id):
        raise NotFoundError("Incident not found")
    return jsonify(resolved=True, id=incident_id)


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=debug_mode)