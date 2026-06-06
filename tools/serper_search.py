"""
Direct Serper /search — called from Python, not via an LLM agent.
Uses ATS-targeted queries so results are individual job postings, not listing pages.
Logs every raw result to stdout so URLs are fully auditable.
"""

import json
import re
import requests

from database import Database
from tools.match_scorer import score_match

_SENIOR = {
    "senior", "sr.", "staff", "principal", "lead", "manager",
    "director", "head of", "vp", "vice president",
    "engineer iii", "engineer iv", "engineer v",
}

# Regex patterns that identify aggregate listing pages (not individual postings)
_LISTING_PAGE_RE = re.compile(
    r"(indeed\.com/(q-|jobs\?)|"
    r"linkedin\.com/jobs/search|"
    r"glassdoor\.com/Job/jobs|"
    r"builtin\w*\.com/jobs/[^/]+/[^/]+/?$|"
    r"ziprecruiter\.com/Jobs|"
    r"monster\.com/jobs/search|"
    r"dice\.com/jobs(?:/search)?|"
    r"simplyhired\.com/search)",
    re.IGNORECASE,
)

# 10 query variations — mix of ATS-targeted and keyword-specific
# These are more likely to surface individual job postings via Google
_QUERY_TEMPLATES = [
    '"{role}" remote -senior -lead site:greenhouse.io',
    '"{role}" remote -senior -lead site:lever.co',
    '"{role}" remote entry level -senior -lead',
    '"junior {role}" OR "mid-level {role}" remote -senior',
    '"ETL engineer" remote -senior -lead site:greenhouse.io',
    '"ETL engineer" OR "pipeline engineer" remote entry level -senior',
    '"analytics engineer" remote entry level -senior -lead',
    '"{role}" remote -senior site:jobs.ashbyhq.com',
    '"data pipeline" engineer remote junior -senior',
    '"{role}" 1-3 years experience remote -senior -lead',
]


def _is_senior(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in _SENIOR)


def _is_listing_page(url: str) -> bool:
    return bool(_LISTING_PAGE_RE.search(url))


_JOB_BOARDS = re.compile(
    r"\b(greenhouse|lever|workday|ashby|jobvite|smartrecruiters?|"
    r"bamboohr|icims|taleo|breezy|recruitee)\b",
    re.IGNORECASE,
)
_ROLE_WORDS = re.compile(
    r"\b(engineer|developer|analyst|scientist|architect|specialist|"
    r"manager|intern|coordinator)\b",
    re.IGNORECASE,
)


def _clean_title(title: str) -> str:
    """Strip 'Job Application for' prefix and trailing ' - Greenhouse' etc."""
    t = re.sub(r"^job application for\s+", "", title, flags=re.IGNORECASE)
    # Remove trailing board name segment: "Role at Co - Greenhouse"
    t = re.sub(r"\s*[-–|]\s*" + _JOB_BOARDS.pattern + r"[\w\s]*$", "", t, flags=re.IGNORECASE)
    return t.strip()


def _extract_company(title: str, display_link: str) -> str:
    """
    Try these in order:
      1. 'Role at Company'  → take everything after ' at '
      2. 'Company - Role - Board'  → first segment that looks like a company name
      3. Domain name from displayLink
    """
    # Clean board suffixes before parsing
    clean = re.sub(r"\s*[-–|]\s*" + _JOB_BOARDS.pattern + r"[\w\s]*$", "", title, flags=re.IGNORECASE)
    clean = re.sub(r"^job application for\s+", "", clean, flags=re.IGNORECASE)

    for sep in [" at ", " @ "]:
        if sep in clean:
            candidate = clean.split(sep, 1)[-1]
            candidate = re.split(r"\s*[|\-–]\s*", candidate)[0].strip()
            if 1 < len(candidate) < 60:
                return candidate

    # Lever / some others: "Company - Role" — first segment is company
    parts = [p.strip() for p in re.split(r"\s*[-–]\s*", clean) if p.strip()]
    if len(parts) >= 2:
        first = parts[0]
        last  = parts[-1]
        # Prefer whichever segment does NOT contain role-like words
        if first and not _ROLE_WORDS.search(first) and len(first) < 50:
            return first
        if last and not _ROLE_WORDS.search(last) and len(last) < 50:
            return last

    domain = re.sub(r"^(www\.|jobs\.|careers\.)", "", display_link.split("/")[0])
    return domain or "Unknown"


def run_job_searches(
    role: str,
    api_key: str,
    db: Database,
    resume_text: str,
    target_new: int = 10,
    results_per_query: int = 5,
) -> list[dict]:
    """
    Run up to 10 Serper queries. Logs every raw result to stdout.
    Deduplicates against the database, skips senior titles and listing pages,
    computes match scores from resume.txt, and saves new jobs.
    Returns the list of newly saved job dicts.
    """
    if not api_key:
        print("[SEARCH] ERROR: SERPER_API_KEY is not set in .env")
        return []

    known_urls: set[str] = {j["url"] for j in db.get_jobs(limit=5000) if j.get("url")}
    print(f"\n[SEARCH] {len(known_urls)} URL(s) already in database — will skip these")

    queries  = [t.format(role=role) for t in _QUERY_TEMPLATES]
    headers  = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    saved: list[dict] = []

    for query in queries:
        if len(saved) >= target_new:
            break

        print(f"\n{'='*62}")
        print(f"[SERPER] Query: {query!r}")
        print(f"{'='*62}")

        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers=headers,
                json={"q": query, "num": results_per_query, "gl": "us", "hl": "en"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            print(f"[SERPER] HTTP error: {e}")
            continue
        except json.JSONDecodeError as e:
            print(f"[SERPER] Bad JSON: {e}")
            continue

        organics = data.get("organic", [])
        print(f"[SERPER] {len(organics)} organic result(s) returned\n")

        for i, item in enumerate(organics, 1):
            url          = (item.get("link")        or "").strip()
            title        = (item.get("title")       or "").strip()
            snippet      = (item.get("snippet")     or "").strip()
            display_link = (item.get("displayLink") or "")

            # ── Raw log — every field, so URLs are fully verifiable ───────────
            print(f"  [{i}] title   : {title!r}")
            print(f"       url     : {url!r}")
            print(f"       domain  : {display_link!r}")
            print(f"       snippet : {snippet[:120]!r}")

            if not url:
                print(f"       -> SKIP (no URL)\n")
                continue
            if _is_listing_page(url):
                print(f"       -> SKIP (aggregate listing page)\n")
                continue
            if url in known_urls:
                print(f"       -> SKIP (already in DB)\n")
                continue
            if _is_senior(title):
                print(f"       -> SKIP (senior-level title)\n")
                continue

            clean_title = _clean_title(title)
            company     = _extract_company(title, display_link)
            match_score = score_match(snippet, resume_text) if snippet and resume_text else None
            job_id      = db.upsert_job(
                title=clean_title,
                company=company,
                url=url,
                location="Remote",
                description=snippet,
                source=f"serper:{query[:40]}",
                match_score=match_score,
            )
            known_urls.add(url)
            saved.append({
                "id": job_id, "title": clean_title, "company": company,
                "url": url, "match_score": match_score,
            })
            print(f"       -> SAVED job_id={job_id}  score={match_score}\n")

            if len(saved) >= target_new:
                break

    print(f"\n[SEARCH] Done — {len(saved)} new job(s) saved this run.")
    return saved
