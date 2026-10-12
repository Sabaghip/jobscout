from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from jobscout.config import fake_llm_mode
from jobscout.llm import get_llm
from jobscout.schemas import ExtractedJob, JobListExtraction, JobPosting, JobSummary

LISTING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You extract open job postings from a company's careers page. You are given the "
            "page's visible text and a list of (link text, href) pairs found on the page. "
            "Identify each distinct open position. Use the links to recover each job's URL - "
            "match it by the job title text. If a job has no dedicated link, reuse the careers "
            "page URL. Skip navigation links, footer links, and anything that isn't an actual "
            "open position (e.g. 'Benefits', 'About us', 'Life at Company'). If the page clearly "
            "lists no open positions, return an empty list.",
        ),
        (
            "human",
            "Careers page URL: {url}\n\n"
            "Visible page text:\n{page_text}\n\n"
            "Links found on page (text, href):\n{links}",
        ),
    ]
)

SUMMARY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You distill a single job posting's page into a compact structured summary, for "
            "someone who will later compare it against a candidate's CV. Only use facts stated "
            "on the page - never invent skills, seniority, or salary that aren't there. Use "
            "'unknown' or an empty list/string for anything not stated.",
        ),
        (
            "human",
            "Job title: {title}\n\nFull page text:\n{description}",
        ),
    ]
)


def _fake_extract(links: list[tuple[str, str]]) -> JobListExtraction:
    jobs = [
        ExtractedJob(title=text, url=href, location="unknown")
        for text, href in links
        if text and len(text) > 3
    ][:5]
    return JobListExtraction(jobs=jobs)


def extract_jobs(url: str, page_text: str, links: list[tuple[str, str]]) -> list[JobPosting]:
    if fake_llm_mode():
        extracted = _fake_extract(links).jobs
    else:
        llm = get_llm().with_structured_output(JobListExtraction)
        links_block = "\n".join(f"- {text!r} -> {href}" for text, href in links) or "(none found)"
        chain = LISTING_PROMPT | llm
        result: JobListExtraction = chain.invoke(
            {"url": url, "page_text": page_text or "(empty)", "links": links_block}
        )
        extracted = result.jobs

    return [JobPosting(**job.model_dump()) for job in extracted]


def summarize_job(title: str, description: str) -> JobSummary:
    if fake_llm_mode():
        return JobSummary(summary=description[:200])

    llm = get_llm().with_structured_output(JobSummary)
    chain = SUMMARY_PROMPT | llm
    return chain.invoke({"title": title, "description": description or "(empty)"})
