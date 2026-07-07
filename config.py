# ─────────────────────────────────────────────────────────────────
# config.py — YOUR personal settings. This is the only file you need to update before running the pipeline.
# ─────────────────────────────────────────────────────────────────


# ── LLM's profile (used by the LLM evaluator) ─────────────────────
#Modify the system prompt here and tailor it to your requirements. Make it the expert you want it to be
SYSTEM_ROLE = (
    """You are a senior recruiter and career coach specialising in <xx,xx,...> roles in <industry>. You give honest, direct assessments.
    You ALWAYS respond with valid JSON only — no markdown, no preamble and no extra text."""
)


# ── Your profile (used by the LLM evaluator) ─────────────────────
"""
!!!!--- Update the prompt below to tailor to your various requirements:
    1. Add in the target primary and secondary roles
    2. Add the Compensation targets, location and visa details (if applicable) or any other relevant details that defines your profile at a glance
    3. Add in as many bullet points with superpowers or highlights from your profile

 """
YOUR_PROFILE = """
Target roles (PRIMARY): [e.g. Senior Data Governance Analyst, GRC Analyst]
Target roles (SECONDARY): [e.g. Senior Data Analyst, AI Governance Analyst]
Compensation target: [$XXX,000–$XXX,000] | Walk-away minimum: [$XXX,000]
Location: [e.g. Remote preferred, open to Hybrid Bay Area CA]
Visa: [e.g. No sponsorship needed]

Superpowers:
1. [Your key strength #1]
2. [Your key strength #2]
3. [Your key strength #3]
"""

# ── Fit Evaluation (used by the LLM evaluator) ─────────────────────
"""
# Tailor these steps to your target roles and deal-breakers.
# Add or remove steps as needed."""

EVALUATION_INSTRUCTIONS = """
Step 1 — Role type check:
- [Describe what a relevant role looks like for you]
- [Describe what roles to cap the score on and why]

Step 2 — Domain expertise check. Apply a HARD PENALTY (-2 points each) if the role
requires skills, tools, or domain knowledge NOT mentioned in the candidate's resume.

Step 3 — Seniority check:
- Role requires significantly more years than shown in the candidate's resume → deduct 1-2 points
- Role is junior/entry level → deduct 3+ points

Step 4 — Strength alignment:
- [List the skills or background signals that should boost the score]

Step 5 — application_priority logic (this CAN factor in salary and location):
- "Apply today": score 8+ AND location matches candidate's preference AND salary meets target or unlisted
- "Apply this week": score 6-7 OR good role but salary/location is uncertain
- "Monitor": score 5-6 OR location doesn't match candidate's preference
- "Skip": score below 5 OR wrong track entirely
"""

# ── Calibration examples (used by the LLM evaluator) ─────────────
# Give 2-3 concrete examples to anchor the scoring scale.
# Be specific since the more grounded these are, the more consistent the scores.
CALIBRATION_EXAMPLES = """
Example A — Score this 4/10 (Stretch):
[Describe a role that looks related but is actually a poor fit and why]

Example B — Score this 8/10 (Strong Fit):
[Describe a role that is a strong match and why — even if salary/location isn't perfect]
"""


# ── Keyword filters (used by the pre-screener) ────────────────────
#!!!---Add the positive keywords for your profile below. Be as detailed and specific as possible ---!!!
POSITIVE_KEYWORDS = [
    "data governance", "grc", "risk", "compliance", # add more...
]

#!!!---Add the negative keywords for your profile below. Be as detailed and specific as possible ---!!!
NEGATIVE_KEYWORDS = [
    "junior", "intern", "software engineer", # add more...
]

#!!!---Add the seniority keywords for your profile below. Be as detailed and specific as possible ---!!!
SENIORITY_BOOST = ["senior", "staff", "lead", "consultant", "specialist",# add more...
]

# Role archetypes edit these to match your target roles. Used to classify job type for resume routing.
# primary = dream role, secondary = good fit, adjacent = stretch/ alternate role names
ROLE_ARCHETYPES = {
    "primary": ["senior data analyst", "grc analyst",], # add more roles here
    "secondary": ["bi engineer", "bi analayst",], # add more roles here
    "adjacent": ["business analyst", "reporting analyst", ], # add more roles here
}


COMP_MINIMUM_USD = 120_000