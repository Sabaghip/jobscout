from __future__ import annotations

import json


def _parse_summary(job: dict) -> dict | None:
    raw = job.get("summary_json") or ""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def format_job_summary(summary: dict) -> str:
    parts: list[str] = []
    if summary.get("summary"):
        parts.append(summary["summary"])
    parts.append(
        f"Seniority: {summary.get('seniority', 'unknown')}  |  "
        f"Remote: {summary.get('remote_policy', 'unknown')}  |  "
        f"Employment: {summary.get('employment_type', 'unknown')}  |  "
        f"Salary: {summary.get('salary_range') or 'not stated'}"
    )
    if summary.get("skills"):
        parts.append("Skills: " + ", ".join(summary["skills"]))
    for field, label in (
        ("responsibilities", "Responsibilities"),
        ("requirements", "Requirements"),
        ("nice_to_have", "Nice to have"),
    ):
        items = summary.get(field) or []
        if items:
            parts.append(label + ":\n" + "\n".join(f"  - {item}" for item in items))
    return "\n\n".join(parts)


def job_detail_text(job: dict) -> str:
    """Full human-readable view: structured summary (if any) plus the raw page text below it."""
    summary = _parse_summary(job)
    parts = [format_job_summary(summary)] if summary else []
    if parts:
        parts.append("\n--- raw page text ---\n")
    parts.append(job.get("description") or "(no description captured)")
    return "\n\n".join(parts)


def job_rating_context(job: dict) -> str:
    """Compact view for LLM rating: the structured summary alone when available, since it
    already distills the raw page - falls back to raw description only when no summary exists
    yet (e.g. a job scanned before the structuring step existed)."""
    summary = _parse_summary(job)
    if summary:
        return format_job_summary(summary)
    return job.get("description") or "(no description captured)"
