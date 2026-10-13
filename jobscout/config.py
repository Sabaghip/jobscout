from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

from jobscout.schemas import Company

PROJECT_ROOT = Path(__file__).resolve().parent.parent
COMPANIES_FILE = PROJECT_ROOT / "companies.yaml"
DB_FILE = PROJECT_ROOT / "jobs.db"

load_dotenv(PROJECT_ROOT / ".env")

CV_FILE = PROJECT_ROOT / os.environ.get("CV_PATH", "cv.tex")


def load_cv_text() -> str:
    """Read the candidate's CV from CV_FILE (LaTeX source is fine as-is - the LLM reads
    past the markup). Point CV_PATH in .env at a different file to use another CV."""
    if not CV_FILE.exists():
        return ""
    return CV_FILE.read_text()


def load_companies() -> list[Company]:
    if not COMPANIES_FILE.exists():
        return []
    data = yaml.safe_load(COMPANIES_FILE.read_text()) or []
    return [Company(**entry) for entry in data]


def save_companies(companies: list[Company]) -> None:
    data = [c.model_dump() for c in companies]
    COMPANIES_FILE.write_text(yaml.safe_dump(data, sort_keys=False))


def add_company(name: str, url: str) -> None:
    companies = load_companies()
    if any(c.url == url for c in companies):
        return
    companies.append(Company(name=name, url=url))
    save_companies(companies)


def llm_provider() -> str:
    return os.environ.get("LLM_PROVIDER", "openai").lower()


def fake_llm_mode() -> bool:
    return os.environ.get("JOBSCOUT_FAKE_LLM", "0") == "1"
