# ─────────────────────────────────────────────────────────────────

"""
job_fetcher.py — FREE job description fetcher using LinkedIn's public guest API.

No Apify. No API key. No cost.

LinkedIn serves job postings to unauthenticated visitors through a public guest endpoint:
  https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}

This is the same data LinkedIn serves to search engines and anonymous browsers.
It works without a session cookie or login, and has been confirmed working in 2026.

Legal note: Scraping publicly accessible data is permissible per the hiQ v. LinkedIn
ruling (9th Circuit) affirming that accessing public data does not violate the CFAA.
"""
# ─────────────────────────────────────────────────────────────────

import re
import time
import random
import requests
from bs4 import BeautifulSoup


# Rotate user agents to behave like a normal browser
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

GUEST_API_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"


def extract_job_id(job_url: str) -> str | None:
    """Extract the numeric job ID from a LinkedIn job URL."""
    match = re.search(r'/jobs/view/(\d+)', job_url)
    return match.group(1) if match else None


def fetch_job_details(job_url: str, job_id: str = None) -> dict:
    """
    Fetch full job details from LinkedIn's public guest API.

    Args:
        job_url: The full LinkedIn job URL
        job_id: Optional — if already extracted, skip URL parsing

    Returns:
        dict with title, company, location, description, company_linkedin_url, job_url, job_id
        Returns empty dict if fetch fails.
    """
    if not job_id:
        job_id = extract_job_id(job_url)
    if not job_id:
        print(f"  ⚠️  Could not extract job ID from: {job_url}")
        return {}

    url = GUEST_API_URL.format(job_id=job_id)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

    # Polite delay — important for not getting rate-limited
    time.sleep(random.uniform(1.5, 3.0))

    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.HTTPError as e:
        if resp.status_code == 429:
            print(f"  ⚠️  Rate limited by LinkedIn. Waiting 30s...")
            time.sleep(30)
            resp = requests.get(url, headers=headers, timeout=20)
        else:
            print(f"  ❌  HTTP error for job {job_id}: {e}")
            return {}
    except requests.RequestException as e:
        print(f"  ❌  Request error for job {job_id}: {e}")
        return {}

    soup = BeautifulSoup(resp.text, "html.parser")

    # ── Extract fields ───────────────────────────────────────────────────────

    # Title — appears in multiple class names across LinkedIn's layouts
    title_el = (
        soup.find("h2", {"class": "top-card-layout__title"}) or
        soup.find("h1", {"class": "topcard__title"}) or
        soup.find("h2", {"class": "topcard__title"})
    )

    # Company name + URL
    company_link = (
        soup.find("a", {"class": "topcard__org-name-link"}) or
        soup.find("a", {"data-tracking-control-name": "public_jobs_topcard-org-name"})
    )
    company_name_el = (
        company_link or
        soup.find("span", {"class": "topcard__flavor"}) or
        soup.find("a", {"class": "topcard__flavor-entity-lockup"})
    )

    # Company LinkedIn URL (strip tracking params)
    company_linkedin_url = ""
    if company_link and company_link.get("href"):
        raw_href = company_link["href"]
        # Normalize to: https://www.linkedin.com/company/slug/
        clean = raw_href.split("?")[0].split("&")[0]
        if "linkedin.com/company/" in clean:
            company_linkedin_url = clean.rstrip("/") + "/"

    # Location
    location_el = (
        soup.find("span", {"class": "topcard__flavor--bullet"}) or
        soup.find("span", {"class": "job-details-jobs-unified-top-card__bullet"})
    )

    # Job description — the big text block
    description_el = (
        soup.find("div", {"class": "show-more-less-html__markup"}) or
        soup.find("div", {"class": "description__text"}) or
        soup.find("section", {"class": "show-more-less-html"}) or
        soup.find("div", {"class": "job-details-jobs-unified-top-card__job-description"})
    )

    # Clean up description: remove "Show more"/"Show less" buttons
    desc_text = ""
    if description_el:
        for btn in description_el.find_all("button"):
            btn.decompose()
        desc_text = description_el.get_text(separator="\n", strip=True)

    # Employment type / seniority (sometimes present)
    criteria = {}
    for item in soup.find_all("li", {"class": "description__job-criteria-item"}):
        header = item.find("h3")
        value = item.find("span")
        if header and value:
            criteria[header.get_text(strip=True).lower()] = value.get_text(strip=True)

    return {
        "title": title_el.get_text(strip=True) if title_el else "",
        "company": company_name_el.get_text(strip=True) if company_name_el else "",
        "company_linkedin_url": company_linkedin_url,
        "location": location_el.get_text(strip=True) if location_el else "",
        "description": desc_text,
        "employment_type": criteria.get("employment type", ""),
        "seniority_level": criteria.get("seniority level", ""),
        "industry": criteria.get("industries", ""),
        "job_url": job_url,
        "job_id": job_id,
    }


def fetch_jobs_batch(job_stubs: list, max_retries: int = 2) -> list:
    """
    Fetch full details for a list of job stubs.
    Each stub must have 'url' and 'job_id' keys.

    Returns list of successfully fetched job dicts.
    """
    results = []
    for i, stub in enumerate(job_stubs):
        print(f"   [{i+1}/{len(job_stubs)}] Fetching: {stub.get('title_hint', stub.get('job_id', '?'))}")

        job = {}
        for attempt in range(max_retries):
            job = fetch_job_details(stub["url"], stub.get("job_id"))
            if job and job.get("description"):
                break
            if attempt < max_retries - 1:
                print(f"   ↺  Retry {attempt+2}/{max_retries}...")
                time.sleep(5)

        if job and job.get("description"):
            # Carry forward metadata from pre-screener
            job["screen"] = stub.get("screen", {})
            results.append(job)
            print(f"   ✅  '{job.get('title', '?')}' @ {job.get('company', '?')}")
        else:
            print(f"   ⚠️  Could not fetch description — skipping")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Replace with any real LinkedIn job ID to test
    test_url = "https://www.linkedin.com/jobs/view/3900000000"
    print("Testing LinkedIn guest API fetch...")
    result = fetch_job_details(test_url)
    if result:
        print(f"Title: {result['title']}")
        print(f"Company: {result['company']}")
        print(f"Location: {result['location']}")
        print(f"Description preview: {result['description'][:300]}...")
    else:
        print("No result (job may have expired or ID is invalid)")
