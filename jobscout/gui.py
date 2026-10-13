from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, simpledialog, ttk

from jobscout.config import add_company, load_companies, load_cv_text
from jobscout.formatting import job_detail_text
from jobscout.rating import rate_stored_job
from jobscout.graph import build_graph
from jobscout.storage import get_all_jobs, get_unrated_jobs, make_job_id, save_rating


class JobScoutApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("JobScout")
        self.root.geometry("1000x600")

        self.events: queue.Queue = queue.Queue()
        self.scanning = False

        self._build_layout()
        self.refresh_companies()
        self.refresh_jobs()
        self.root.after(200, self._poll_events)

    def _build_layout(self) -> None:
        left = ttk.Frame(self.root, padding=8)
        left.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(left, text="Companies", font=("", 11, "bold")).pack(anchor="w")
        self.company_list = tk.Listbox(left, width=28, height=20, exportselection=False)
        self.company_list.pack(fill=tk.Y, expand=True, pady=(4, 8))

        ttk.Button(left, text="Add company", command=self.on_add_company).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Scan selected", command=self.on_scan_selected).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Scan all", command=self.on_scan_all).pack(fill=tk.X, pady=2)
        ttk.Button(left, text="Rate new jobs", command=self.on_rate_new).pack(fill=tk.X, pady=(12, 2))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(left, textvariable=self.status_var, foreground="gray", wraplength=200).pack(
            anchor="w", pady=(12, 0)
        )

        right = ttk.Frame(self.root, padding=8)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        filter_row = ttk.Frame(right)
        filter_row.pack(fill=tk.X)
        ttk.Label(filter_row, text="Filter:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self.refresh_jobs())
        ttk.Entry(filter_row, textvariable=self.filter_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)

        columns = ("company", "title", "location", "department", "fit", "first_seen")
        tree_frame = ttk.Frame(right)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=14)
        for col, width in zip(columns, (140, 300, 120, 120, 60, 140)):
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self.on_open_job)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_job)
        self.tree.tag_configure("new", background="#e6ffe6")

        ttk.Label(right, text="Double-click a row to open the job posting", foreground="gray").pack(
            anchor="w", pady=(4, 0)
        )

        ttk.Label(right, text="Description", font=("", 10, "bold")).pack(anchor="w", pady=(8, 0))
        desc_frame = ttk.Frame(right)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        desc_scroll = ttk.Scrollbar(desc_frame, orient=tk.VERTICAL)
        self.description_text = tk.Text(
            desc_frame, height=10, wrap=tk.WORD, yscrollcommand=desc_scroll.set, state=tk.DISABLED
        )
        desc_scroll.config(command=self.description_text.yview)
        self.description_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        desc_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self._job_urls: dict[str, str] = {}
        self._job_descriptions: dict[str, str] = {}
        self._new_job_ids: set[str] = set()

    def refresh_companies(self) -> None:
        self.company_list.delete(0, tk.END)
        for company in load_companies():
            self.company_list.insert(tk.END, f"{company.name}  ({company.url})")
        self._companies = load_companies()

    def refresh_jobs(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self._job_urls.clear()
        self._job_descriptions.clear()
        needle = self.filter_var.get().lower().strip()
        for job in get_all_jobs():
            haystack = f"{job['company']} {job['title']} {job['location']}".lower()
            if needle and needle not in haystack:
                continue
            tags = ("new",) if job["id"] in self._new_job_ids else ()
            rating = None
            if job.get("rating_json"):
                try:
                    rating = json.loads(job["rating_json"])
                except json.JSONDecodeError:
                    rating = None
            fit = str(rating["score"]) if rating else ""
            self.tree.insert(
                "",
                tk.END,
                iid=job["id"],
                values=(job["company"], job["title"], job["location"], job["department"], fit, job["first_seen"]),
                tags=tags,
            )
            self._job_urls[job["id"]] = job["url"]
            detail = job_detail_text(job)
            if rating:
                rating_block = (
                    f"Fit score: {rating['score']}/100\n\n"
                    f"{rating.get('reasoning', '')}\n\n"
                    + "Positives:\n" + "\n".join(f"  + {p}" for p in rating.get("positives", []))
                    + "\n\nNegatives:\n" + "\n".join(f"  - {n}" for n in rating.get("negatives", []))
                    + "\n\n--- job details ---\n\n"
                )
                detail = rating_block + detail
            self._job_descriptions[job["id"]] = detail
        self._set_description_text("")

    def on_open_job(self, _event) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        url = self._job_urls.get(selected[0])
        if url:
            webbrowser.open(url)

    def on_select_job(self, _event) -> None:
        selected = self.tree.selection()
        if not selected:
            self._set_description_text("")
            return
        self._set_description_text(self._job_descriptions.get(selected[0], ""))

    def _set_description_text(self, text: str) -> None:
        self.description_text.config(state=tk.NORMAL)
        self.description_text.delete("1.0", tk.END)
        self.description_text.insert("1.0", text)
        self.description_text.config(state=tk.DISABLED)

    def on_add_company(self) -> None:
        name = simpledialog.askstring("Add company", "Company name:", parent=self.root)
        if not name:
            return
        url = simpledialog.askstring("Add company", "Careers page URL:", parent=self.root)
        if not url:
            return
        add_company(name, url)
        self.refresh_companies()

    def on_scan_selected(self) -> None:
        selection = self.company_list.curselection()
        if not selection:
            messagebox.showinfo("JobScout", "Select a company first.")
            return
        company = self._companies[selection[0]]
        self._start_scan([company])

    def on_scan_all(self) -> None:
        companies = load_companies()
        if not companies:
            messagebox.showinfo("JobScout", "Add a company first.")
            return
        self._start_scan(companies)

    def on_rate_new(self) -> None:
        if not load_cv_text():
            messagebox.showinfo("JobScout", "No CV found. Add your LaTeX CV to cv.tex first (see README).")
            return
        if self.scanning:
            messagebox.showinfo("JobScout", "Already busy with a scan/rating run.")
            return
        self.scanning = True
        thread = threading.Thread(target=self._rate_worker, daemon=True)
        thread.start()

    def _rate_worker(self) -> None:
        jobs = get_unrated_jobs()
        if not jobs:
            self.events.put(("status", "Nothing to rate."))
            self.events.put(("done", None))
            return
        for i, job in enumerate(jobs, 1):
            self.events.put(("status", f"Rating {i}/{len(jobs)}: {job['title']}..."))
            try:
                rating = rate_stored_job(job)
                save_rating(job["id"], rating)
            except Exception as exc:  # noqa: BLE001 - surface any failure to the UI instead of dying silently
                self.events.put(("status", f"Error rating {job['title']}: {exc}"))
                continue
        self.events.put(("rated", None))
        self.events.put(("done", None))

    def _start_scan(self, companies) -> None:
        if self.scanning:
            messagebox.showinfo("JobScout", "A scan is already running.")
            return
        self.scanning = True
        thread = threading.Thread(target=self._scan_worker, args=(companies,), daemon=True)
        thread.start()

    def _scan_worker(self, companies) -> None:
        graph = build_graph()
        for company in companies:
            self.events.put(("status", f"Scanning {company.name}..."))
            try:
                result = graph.invoke({"company": company.name, "url": company.url, "errors": []})
            except Exception as exc:  # noqa: BLE001 - surface any failure to the UI instead of dying silently
                self.events.put(("status", f"Error scanning {company.name}: {exc}"))
                continue
            new_jobs = result.get("new_jobs", [])
            self.events.put(("new_jobs", new_jobs, company.name))
            for err in result.get("errors", []):
                self.events.put(("status", f"{company.name}: {err}"))
        self.events.put(("done", None))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "status":
                    self.status_var.set(event[1])
                elif kind == "new_jobs":
                    _, new_jobs, company_name = event
                    if new_jobs:
                        self.status_var.set(f"{company_name}: {len(new_jobs)} new job(s)")
                        for job in new_jobs:
                            self._new_job_ids.add(make_job_id(company_name, job))
                    self.refresh_jobs()
                elif kind == "rated":
                    self.refresh_jobs()
                elif kind == "done":
                    self.scanning = False
                    self.status_var.set("Ready")
        except queue.Empty:
            pass
        self.root.after(200, self._poll_events)


def main() -> None:
    root = tk.Tk()
    JobScoutApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
