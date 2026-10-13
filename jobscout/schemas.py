from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field


class ExtractedJob(BaseModel):
    """What the listing-page LLM call produces - just enough to find and visit each job."""

    title: str = Field(description="Job title as shown on the page")
    url: str = Field(description="Absolute link to the job posting, or the careers page URL if none exists")
    location: str = Field(default="unknown", description="Location or 'remote', 'unknown' if not stated")
    department: str = Field(default="", description="Team/department if stated, else empty string")
    posted_date: str = Field(default="", description="Date posted if stated on the page, else empty string")


class JobListExtraction(BaseModel):
    jobs: list[ExtractedJob] = Field(default_factory=list)


class JobSummary(BaseModel):
    """Compact, structured distillation of a job's own posting page.

    Produced once per job (not re-sent to an LLM on every rescan or future rating
    pass) so later work (e.g. CV matching) reads a few hundred tokens of signal
    instead of the full noisy raw page every time.
    """

    summary: str = Field(default="", description="2-3 sentence plain summary of the role")
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list, description="Specific technologies/tools/languages mentioned")
    seniority: str = Field(default="unknown", description="e.g. 'junior', 'mid', 'senior', 'lead', 'unknown'")
    remote_policy: str = Field(default="unknown", description="e.g. 'remote', 'hybrid', 'onsite', 'unknown'")
    employment_type: str = Field(default="unknown", description="e.g. 'full-time', 'contract', 'internship'")
    salary_range: str = Field(default="", description="As stated on the page, else empty string")


class JobPosting(BaseModel):
    title: str = Field(description="Job title as shown on the page")
    url: str = Field(description="Absolute link to the job posting, or the careers page URL if none exists")
    location: str = Field(default="unknown", description="Location or 'remote', 'unknown' if not stated")
    department: str = Field(default="", description="Team/department if stated, else empty string")
    posted_date: str = Field(default="", description="Date posted if stated on the page, else empty string")
    description: str = Field(
        default="", description="Full raw visible text of the job's own posting page, kept as a lossless fallback"
    )
    summary: JobSummary | None = Field(
        default=None, description="Structured distillation of description, filled in once when the job is new"
    )


class JobRating(BaseModel):
    """How well a job fits the candidate's CV, produced once per job per CV."""

    score: int = Field(ge=0, le=100, description="0-100 fit score between the CV and the job")
    positives: list[str] = Field(default_factory=list, description="Concrete matches: skills/experience that fit")
    negatives: list[str] = Field(default_factory=list, description="Concrete gaps or mismatches")
    reasoning: str = Field(default="", description="One-paragraph explanation grounded in the CV and job text")


class Company(BaseModel):
    name: str
    url: str


class ScrapeState(TypedDict, total=False):
    company: str
    url: str
    page_text: str
    links: list[tuple[str, str]]
    jobs: list[JobPosting]
    new_jobs: list[JobPosting]
    errors: list[str]
