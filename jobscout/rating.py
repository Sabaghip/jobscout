from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from jobscout.config import fake_llm_mode, load_cv_text
from jobscout.formatting import job_rating_context
from jobscout.llm import get_llm
from jobscout.schemas import JobRating

RATING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are helping a job seeker evaluate how well an open position fits their CV. "
            "You are given the candidate's CV (likely LaTeX source - ignore the markup, read "
            "the content) and a job posting. Compare the job's requirements against the "
            "candidate's actual experience and skills. Give a 0-100 fit score, a short list of "
            "concrete positives (skills/experience that match), a short list of concrete "
            "negatives (gaps, mismatches, or missing requirements), and a one-paragraph "
            "reasoning. Be honest and specific - ground every point in something actually "
            "stated in the CV or the job posting, never invent a skill the candidate doesn't "
            "list.",
        ),
        (
            "human",
            "Candidate CV:\n{cv_text}\n\nJob title: {title}\n\nJob details:\n{job_text}",
        ),
    ]
)


def _fake_rate() -> JobRating:
    return JobRating(score=50, positives=["fake mode"], negatives=["fake mode"], reasoning="fake mode stub")


def rate_job(cv_text: str, title: str, job_text: str) -> JobRating:
    if fake_llm_mode():
        return _fake_rate()

    llm = get_llm().with_structured_output(JobRating)
    chain = RATING_PROMPT | llm
    return chain.invoke({"cv_text": cv_text or "(no CV provided)", "title": title, "job_text": job_text or "(empty)"})


def rate_stored_job(job: dict) -> JobRating:
    cv_text = load_cv_text()
    job_text = job_rating_context(job)
    return rate_job(cv_text, job["title"], job_text)
