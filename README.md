# JobScout

Tracks open positions on company career pages. You give it a list of companies and
their careers URL; it scrapes each page with Playwright, uses an LLM (via LangChain +
LangGraph) to turn the mess into structured job listings, and stores everything in
SQLite. A Tkinter GUI (or the CLI) lets you browse what it found.

## How it works

Each company run goes through a small LangGraph pipeline (`jobscout/graph.py`):

```
scrape -> extract -> describe -> structure -> store
```

- **scrape** - Playwright loads the careers listing page (scrolls, tries "load more"
  buttons), grabs the visible text and every link on the page.
- **extract** - one LLM call turns that page into a list of jobs (title, url,
  location, department, posted date).
- **describe** - Playwright visits each job's own posting page and saves its full
  raw text. No LLM call here - it's free, and re-run on every scan.
- **structure** - one LLM call *per new job only* that distills the raw text into a
  compact `JobSummary` (responsibilities, requirements, nice-to-have, skills,
  seniority, remote policy, employment type, salary). Jobs already in the database
  are skipped here, so rescans don't keep re-paying for unchanged postings.
- **store** - upserts into `jobs.db` (SQLite), tracking first/last seen and which
  jobs are new since the last scan.

Cost per scan: 1 LLM call per company + 1 LLM call per brand-new job found. Already-seen
jobs cost nothing extra on a rescan.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

Copy `.env.example` to `.env` and fill in a real API key:

```
LLM_PROVIDER=openai          # or anthropic
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
```

Note: this needs a Developer API key (platform.openai.com / console.anthropic.com),
not a ChatGPT Plus / Claude Pro subscription - those are separate products with
separate billing.

The Tkinter GUI needs the system Tk package, which isn't bundled with Python on
Debian/Ubuntu:

```
sudo apt install -y python3-tk
```

## Usage

CLI (`jobscout/cli.py`):

```
python3 main.py add "Some Company" "https://somecompany.com/careers"
python3 main.py list                       # configured companies
python3 main.py scan                       # scan every configured company
python3 main.py scan --company "Some Company"
python3 main.py jobs                       # list everything stored
python3 main.py jobs --company "Some Company"
python3 main.py forget --company "Some Company"   # delete so next scan re-fetches
python3 main.py forget --all
```

GUI:

```
python3 main.py
```

Add companies, hit "Scan selected" / "Scan all", and click a job row to see its
structured summary + full raw description. Double-click opens the posting in your
browser.

## Testing without burning API calls

Set `JOBSCOUT_FAKE_LLM=1` to skip real LLM calls and use a deterministic stub
extractor/summarizer - useful for checking the scrape/store wiring works before
spending real tokens.

## Status

Scraping, structured extraction, and storage are done. CV-based rating (scoring each
job against a resume) is planned but not yet implemented - `description` and
`summary` are already being captured so that feature won't need to re-scrape anything.
