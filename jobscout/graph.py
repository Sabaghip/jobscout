from __future__ import annotations

from langgraph.graph import END, StateGraph

from jobscout.extractor import extract_jobs, summarize_job
from jobscout.schemas import ScrapeState
from jobscout.scraper import scrape_careers_page, scrape_job_page_text
from jobscout.storage import is_known, upsert_jobs


def scrape_node(state: ScrapeState) -> dict:
    page_text, links, errors = scrape_careers_page(state["url"])
    return {"page_text": page_text, "links": links, "errors": state.get("errors", []) + errors}


def extract_node(state: ScrapeState) -> dict:
    if not state.get("page_text") and not state.get("links"):
        return {"jobs": [], "errors": state.get("errors", []) + ["no page content to extract from, skipping"]}
    jobs = extract_jobs(state["url"], state.get("page_text", ""), state.get("links", []))
    return {"jobs": jobs}


def describe_node(state: ScrapeState) -> dict:
    """Fetch each job's own posting page so the full description is saved for later
    (e.g. CV matching), not just the title/location picked off the listing page."""
    jobs = state.get("jobs", [])
    errors = list(state.get("errors", []))
    for job in jobs:
        if not job.url or job.url == state["url"]:
            job.description = state.get("page_text", "")
            continue
        text, errs = scrape_job_page_text(job.url)
        job.description = text
        errors.extend(errs)
    return {"jobs": jobs, "errors": errors}


def structure_node(state: ScrapeState) -> dict:
    """Distill each new job's raw description into a compact JobSummary, once.

    Jobs already stored from a previous scan are skipped - their summary doesn't
    need to be recomputed every rescan, only their raw description is refreshed."""
    jobs = state.get("jobs", [])
    for job in jobs:
        if is_known(state["company"], job):
            continue
        job.summary = summarize_job(job.title, job.description)
    return {"jobs": jobs}


def store_node(state: ScrapeState) -> dict:
    new_jobs = upsert_jobs(state["company"], state.get("jobs", []))
    return {"new_jobs": new_jobs}


def build_graph():
    graph = StateGraph(ScrapeState)
    graph.add_node("scrape", scrape_node)
    graph.add_node("extract", extract_node)
    graph.add_node("describe", describe_node)
    graph.add_node("structure", structure_node)
    graph.add_node("store", store_node)

    graph.set_entry_point("scrape")
    graph.add_edge("scrape", "extract")
    graph.add_edge("extract", "describe")
    graph.add_edge("describe", "structure")
    graph.add_edge("structure", "store")
    graph.add_edge("store", END)

    return graph.compile()
