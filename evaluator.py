# ─────────────────────────────────────────────────────────────────

"""
evaluator.py — Job fit evaluator using Groq API (Llama 3.3 70B). FREE.
No credit card. No cost. Sign up at console.groq.com with email or Google.
 
Rate limit note: free tier = 6,000 tokens/minute.
GROQ_CALL_DELAY=35 in .env keeps us safely within that limit.
"""

# ─────────────────────────────────────────────────────────────────


import json
import re
import os
import time
from groq import Groq
from dotenv import load_dotenv
from pre_screener import  get_archetype_fit, check_salary_mention
from config import SYSTEM_ROLE,YOUR_PROFILE, EVALUATION_INSTRUCTIONS, CALIBRATION_EXAMPLES

load_dotenv()
 
client = Groq(api_key=os.getenv('GROQ_API_KEY'))
MODEL  = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
DELAY  = float(os.getenv('GROQ_CALL_DELAY', '35'))
 
_last_call = 0.0   # module-level timestamp for rate limiting
 
 
# ── Resume loader ─────────────────────────────────────────────────────────────
 
def load_resume() -> str:
    path = 'resume.txt'
    if not os.path.exists(path):
        raise FileNotFoundError("'resume.txt' not found. Add your resume as resume.txt in the project root.")
    with open(path) as f:
        return f.read()
 
# ── Prompt ────────────────────────────────────────────────────────────────────
 


PROMPT = """Evaluate this job posting against the resume.
 
## PROFILE
{profile}
 
Role archetype for this job: {archetype_fit}
 
##  RESUME
{resume}
 
## JOB POSTING
Title: {title}
Company: {company}
Location: {location}
Salary info: {salary_note}
Description:
{description}
 
## INSTRUCTIONS
 
{instructions}
 
## CALIBRATION EXAMPLES
 
{calibration_examples}

Return ONLY this JSON, no other text:
{{
  "fit_score": <1-10>,
  "fit_tier": "<Strong Fit|Good Fit|Stretch|Poor Fit>",
  "fit_summary": "<2-3 honest sentences — be specific about WHY it fits or doesn't>",
  "role_archetype_match": "{archetype_fit}",
  "matching_strengths": ["<specific strength 1>", "<strength 2>", "<strength 3>"],
  "skill_gaps": ["<gap 1>", "<gap 2 if any>"],
  "resume_updates_needed": [
    {{
      "section": "<Skills|Experience|Summary|Certifications>",
      "bullet_or_field": "<which line>",
      "suggestion": "<exact wording to add — be specific>"
    }}
  ],
  "compensation_flag": "<Likely meets target|Below minimum|No salary listed>",
  "location_flag": "<Remote|Hybrid preferred|Onsite — needs consideration|Unknown>",
  "seniority_flag": "<Appropriate level|Too junior|Too senior|Unclear>",
  "is_worth_applying": <true|false>,
  "application_priority": "<Apply today|Apply this week|Monitor|Skip>",
  "recommended_approach": "<one sentence on how to position for this role>"
}}
 
Scoring: 9-10=perfect match, core frameworks required and present; 7-8=strong fit, minor gaps only; 5-6=decent overlap but missing key domain requirements; 3-4=wrong domain or major skill gaps; 1-2=wrong track entirely."""
 
 
# ── Core function ─────────────────────────────────────────────────────────────
 
def evaluate_job(job: dict,  archetype_fit: str = None) -> dict:
    global _last_call
 
    title       = job.get('title', '')
    description = job.get('description', '')
 
    if not archetype_fit:
        archetype_fit = get_archetype_fit(title)
 
    resume = load_resume()

    
    salary = check_salary_mention(description)
 
    prompt = PROMPT.format(
        profile = YOUR_PROFILE,
        resume=resume,
        instructions = EVALUATION_INSTRUCTIONS,
        calibration_examples = CALIBRATION_EXAMPLES,
        title=title,
        company=job.get('company', ''),
        location=job.get('location', ''),
        salary_note=salary['note'],
        description=description[:5000],
        archetype_fit=archetype_fit
    )
 
    # Respect token-per-minute limit
    elapsed = time.time() - _last_call
    if elapsed < DELAY:
        time.sleep(DELAY - elapsed)
 
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': SYSTEM_ROLE},
            {'role': 'user',   'content': prompt},
        ],
        max_tokens=1200,
        temperature=0.2,
    )
    _last_call = time.time()
 
    raw = response.choices[0].message.content
 
    # Parse JSON — handle any extra text the model might add
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw)
        try:
            result = json.loads(match.group()) if match else {}
        except Exception:
            result = {'error': 'parse failed', 'raw': raw[:300]}
 
    # Normalise fit_tier — Groq sometimes goes off-script
    tier = result.get('fit_tier', '')
    tier_lower = tier.lower()
    if any(w in tier_lower for w in ['strong', 'excellent', 'great', 'perfect']):
        result['fit_tier'] = 'Strong Fit'
    elif any(w in tier_lower for w in ['good', 'decent', 'solid', 'overlap', 'moderate']):
        result['fit_tier'] = 'Good Fit'
    elif any(w in tier_lower for w in ['stretch', 'partial', 'some']):
        result['fit_tier'] = 'Stretch'
    elif any(w in tier_lower for w in ['poor', 'weak', 'low', 'wrong']):
        result['fit_tier'] = 'Poor Fit'
 
    # Normalise application_priority
    pri = result.get('application_priority', '')
    pri_lower = pri.lower()
    if 'today' in pri_lower:
        result['application_priority'] = 'Apply today'
    elif 'week' in pri_lower:
        result['application_priority'] = 'Apply this week'
    elif 'monitor' in pri_lower or 'watch' in pri_lower:
        result['application_priority'] = 'Monitor'
    elif 'skip' in pri_lower or 'pass' in pri_lower or 'not' in pri_lower:
        result['application_priority'] = 'Skip'
 
    result['salary_check']        = salary
    result['job_url']             = job.get('job_url', '')
    return result
