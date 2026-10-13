from __future__ import annotations

import argparse
import json
import sys

from jobscout.config import CV_FILE, add_company, load_companies, load_cv_text
from jobscout.graph import build_graph
from jobscout.rating import rate_stored_job
from jobscout.storage import delete_jobs, get_all_jobs, get_unrated_jobs, save_rating


def cmd_add(args: argparse.Namespace) -> None:
    add_company(args.name, args.url)
    print(f"Added {args.name} -> {args.url}")


def cmd_list(args: argparse.Namespace) -> None:
    companies = load_companies()
    if not companies:
        print("No companies configured yet. Use: jobscout add <name> <url>")
        return
    for c in companies:
        print(f"{c.name}: {c.url}")


def cmd_scan(args: argparse.Namespace) -> None:
    companies = load_companies()
    if args.company:
        companies = [c for c in companies if c.name == args.company]
        if not companies:
            print(f"No configured company named {args.company!r}")
            sys.exit(1)

    graph = build_graph()
    for company in companies:
        print(f"Scanning {company.name} ({company.url})...")
        result = graph.invoke({"company": company.name, "url": company.url, "errors": []})
        for err in result.get("errors", []):
            print(f"  ! {err}")
        new_jobs = result.get("new_jobs", [])
        total = len(result.get("jobs", []))
        print(f"  {total} open position(s) found, {len(new_jobs)} new")
        for job in new_jobs:
            print(f"    + {job.title} ({job.location}) {job.url}")


def cmd_jobs(args: argparse.Namespace) -> None:
    jobs = get_all_jobs(args.company)
    if not jobs:
        print("No jobs stored yet. Run `jobscout scan` first.")
        return
    for job in jobs:
        score = ""
        if job.get("rating_json"):
            try:
                score = f" [fit: {json.loads(job['rating_json'])['score']}/100]"
            except (json.JSONDecodeError, KeyError):
                pass
        print(f"[{job['company']}] {job['title']} - {job['location']} - {job['url']}{score}")


def cmd_rate(args: argparse.Namespace) -> None:
    if not load_cv_text():
        print(f"No CV found at {CV_FILE}. Add your LaTeX CV there first (see .env's CV_PATH to use a different file).")
        sys.exit(1)

    jobs = get_all_jobs(args.company) if args.force else get_unrated_jobs(args.company)
    if not jobs:
        print("Nothing to rate.")
        return

    for job in jobs:
        print(f"Rating {job['title']} ({job['company']})...")
        rating = rate_stored_job(job)
        save_rating(job["id"], rating)
        print(f"  score: {rating.score}/100")
        for pos in rating.positives:
            print(f"    + {pos}")
        for neg in rating.negatives:
            print(f"    - {neg}")


def cmd_forget(args: argparse.Namespace) -> None:
    if not args.company and not args.all:
        print("Specify --company <name> or --all (safety check against wiping by accident)")
        sys.exit(1)
    count = delete_jobs(args.company)
    scope = args.company or "all companies"
    print(f"Deleted {count} job(s) for {scope}. Next scan will treat them as new again.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="jobscout")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="Add a company careers page to track")
    p_add.add_argument("name")
    p_add.add_argument("url")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List configured companies")
    p_list.set_defaults(func=cmd_list)

    p_scan = sub.add_parser("scan", help="Scrape configured companies for open positions")
    p_scan.add_argument("--company", help="Only scan this company")
    p_scan.set_defaults(func=cmd_scan)

    p_jobs = sub.add_parser("jobs", help="List stored jobs")
    p_jobs.add_argument("--company", help="Only show this company's jobs")
    p_jobs.set_defaults(func=cmd_jobs)

    p_forget = sub.add_parser("forget", help="Delete stored jobs so the next scan re-fetches them")
    p_forget.add_argument("--company", help="Only delete this company's jobs")
    p_forget.add_argument("--all", action="store_true", help="Delete every stored job")
    p_forget.set_defaults(func=cmd_forget)

    p_rate = sub.add_parser("rate", help="Rate stored jobs against your CV")
    p_rate.add_argument("--company", help="Only rate this company's jobs")
    p_rate.add_argument("--force", action="store_true", help="Re-rate jobs that already have a rating")
    p_rate.set_defaults(func=cmd_rate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
