# ─────────────────────────────────────────────────────────────────

"""
pre_screener.py — Fast keyword-based job pre-screening using config.py filters.

This runs BEFORE calling Groq or any paid API, filtering out irrelevant roles based on keyword lists defined in config.py.
"""


"""Read the comments thoroughly to understand where exactly to make updates through the code.

Change to be made only under the QUICK TEST section """


# ─────────────────────────────────────────────────────────────────


import re
from config import POSITIVE_KEYWORDS, NEGATIVE_KEYWORDS, SENIORITY_BOOST, ROLE_ARCHETYPES, COMP_MINIMUM_USD

def get_archetype_fit(title: str) -> str:
    """
    Check if the job title matches one of the defined role archetypes in config.py.
    """
    title_lower = title.lower()
    for fit_level, archetypes in ROLE_ARCHETYPES.items():
        if any(archetype in title_lower for archetype in archetypes):
            return fit_level
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Main screening function
# ─────────────────────────────────────────────────────────────────────────────

def screen_job(title: str, description: str = "") -> dict:
    """
    Run a fast keyword pre-screen on a job title + description.

    Returns a dict:
    {
        "pass": bool,               # True = send to Groq, False = skip
        "reason": str,              # Why it passed or failed
        "archetype_fit": str,       # primary / secondary / adjacent / unknown
        "has_seniority": bool,      # Whether title contains a seniority boost
        "negative_hit": str | None, # Which negative keyword triggered (if any)
        "positive_hit": str | None, # Which positive keyword matched
    }
    """
    title_lower = title.lower()
    text_lower = (title + " " + description).lower()

    # 1. Check negative keywords first — instant fail
    for neg in NEGATIVE_KEYWORDS:
        if neg.strip() in title_lower:
            return {
                "pass": False,
                "reason": f"Negative keyword match in title: '{neg.strip()}'",
                "archetype_fit": None,
                "has_seniority": False,
                "negative_hit": neg.strip(),
                "positive_hit": None,
            }

    # 2. Check positive keywords — need at least one match
    matched_positive = None
    for pos in POSITIVE_KEYWORDS:
        if pos in text_lower:
            matched_positive = pos
            break

    if not matched_positive:
        return {
            "pass": False,
            "reason": "No positive keyword match in title or description",
            "archetype_fit": None,
            "has_seniority": False,
            "negative_hit": None,
            "positive_hit": None,
        }

    # 3. Check archetype fit
    archetype_fit = get_archetype_fit(title)

    # 4. Check seniority
    has_seniority = any(s in title_lower for s in SENIORITY_BOOST)

    return {
        "pass": True,
        "reason": f"Positive keyword match: '{matched_positive}' | Fit: {archetype_fit}",
        "archetype_fit": archetype_fit,
        "has_seniority": has_seniority,
        "negative_hit": None,
        "positive_hit": matched_positive,
    }


def screen_job_list(jobs: list) -> tuple[list, list]:
    """
    Screen a list of job dicts. Each dict must have 'title' key; optionally 'description'.
    Returns (passed_jobs, rejected_jobs) — each item includes the screen result.
    """
    passed, rejected = [], []

    for job in jobs:
        title = job.get("title", job.get("title_hint", ""))
        description = job.get("description", "")
        result = screen_job(title, description)
        job["screen"] = result

        if result["pass"]:
            passed.append(job)
        else:
            rejected.append(job)

    print(f"🔍 Pre-screen: {len(passed)} passed, {len(rejected)} filtered out "
          f"(saved ~{len(rejected)} Groq API calls)")
    return passed, rejected


def check_salary_mention(description: str) -> dict:
    """
    If a job description mentions salary, check it against minimum set in config.py (COMP_MINIMUM_USD).
    Returns dict with 'found', 'value', and 'meets_minimum'.
    """
    patterns = [
        r'\$(\d{2,3})[Kk]',                        # $120K
        r'\$(\d{3},\d{3})',                          # $120,000
        r'(\d{2,3})[Kk]\s*[-–]\s*(\d{2,3})[Kk]',  # 120K-150K
        r'(\d{3},\d{3})\s*[-–]\s*(\d{3},\d{3})',   # 120,000 - 150,000
    ]

    for pattern in patterns:
        match = re.search(pattern, description)
        if match:
            try:
                raw = match.group(1).replace(',', '')
                value = int(raw) * 1000 if int(raw) < 1000 else int(raw)
                meets = value >= COMP_MINIMUM_USD
                return {
                    "found": True,
                    "value": value,
                    "meets_minimum": meets,
                    "note": f"Found ${value:,} — {'✅ meets' if meets else '⚠️ below'} your ${COMP_MINIMUM_USD:,} minimum"
                }
            except Exception:
                pass

    return {"found": False, "value": None, "meets_minimum": True, "note": "No salary mentioned"}


# ─────────────────────────────────────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────────────────────────────────────
#!!!--- Update the test cases below to have a dummy test use case for validation of the code ---!!!
if __name__ == "__main__":
    test_cases = [
        ("[Your primary role title]", "[Keywords from a strong match JD]"),
        ("[Your secondary role title]", "[Keywords from a decent match JD]"),
        ("[A role with a negative keyword]", "some description"),
        ("[An entry level / intern role]", "entry level description"),
    ]

    for title, desc in test_cases:
        result = screen_job(title, desc)
        status = "✅ PASS" if result["pass"] else "❌ SKIP"
        print(f"{status} | {title}")
        print(f"       → {result['reason']}")
        if result["pass"]:
            print(f"       → Archetype: {result['archetype_fit']}")  
        print()
