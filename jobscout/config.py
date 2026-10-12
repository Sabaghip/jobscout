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
