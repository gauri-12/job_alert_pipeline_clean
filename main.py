# ─────────────────────────────────────────────────────────────────

"""
main.py — Daily LinkedIn Job Alert Evaluation Pipeline.

Usage:
  python main.py              # full run
  python main.py --dry-run    # parse emails + pre-screen only, no API calls
  python main.py --test       # run one test evaluation to verify Groq is working
"""

"""Read the comments thoroughly to understand where exactly to make updates through the code.

Change to be made only in lines 182 to 188 for validation of code """


# ─────────────────────────────────────────────────────────────────


import os
import sys
import time
from datetime import date
from dotenv import load_dotenv

load_dotenv()

from gmail_reader   import get_gmail_service, get_linkedin_alert_emails, parse_jobs_from_email
from job_fetcher    import fetch_job_details
from pre_screener   import screen_job_list
from evaluator      import evaluate_job
from sheets_logger  import log_job
from digest_sender  import build_digest_html, send_digest

MIN_FIT_SCORE = int(os.getenv('MIN_FIT_SCORE', '6'))
DRY_RUN       = '--dry-run' in sys.argv
TEST_MODE     = '--test' in sys.argv


def run_pipeline():
    print(f'\n{"="*55}')
    print(f'  🚀 Job Alert Pipeline — {date.today()}')
    if DRY_RUN:
        print('  ⚠️  DRY RUN — no Groq or Sheets calls')
    print(f'{"="*55}\n')

    # ── 1. Read Gmail ────────────────────────────────────────
    print('📧 Step 1: Reading LinkedIn alert emails...')
    service = get_gmail_service()
    emails  = get_linkedin_alert_emails(service)
    print(f'   Found {len(emails)} alert email(s)')

    if not emails:
        print('   No new emails. Exiting.')
        return

    # Extract all job URLs from all emails
    all_stubs = []
    for email in emails:
        stubs = parse_jobs_from_email(service, email['id'])
        all_stubs.extend(stubs)

    # Deduplicate
    seen, unique = set(), []
    for s in all_stubs:
        if s['job_id'] not in seen:
            seen.add(s['job_id'])
            unique.append(s)
    print(f'   Extracted {len(unique)} unique job URL(s)\n')

    if not unique:
        print('   No job URLs found in emails. Exiting.')
        return

    # ── 2. Fetch full job descriptions ───────────────────────
    print('📄 Step 2: Fetching full job descriptions...')
    full_jobs = []
    for i, stub in enumerate(unique):
        print(f'   [{i+1}/{len(unique)}] fetching {stub["job_id"]}...', end='', flush=True)
        try:
            job = fetch_job_details(stub['url'], stub['job_id'])
            if job and job.get('description'):
                full_jobs.append(job)
                print(f' ✅ {job.get("title","?")} @ {job.get("company","?")}')
            else:
                print(' ⚠️  Empty — skipping')
        except Exception as e:
            print(f' ❌ {e}')
        time.sleep(0.5)
    print(f'\n   Fetched {len(full_jobs)} job(s) with descriptions\n')

    if not full_jobs:
        print('   No jobs fetched. Exiting.')
        return

    # ── 3. Pre-screen (free, keyword filter on real titles) ───
    print('🔍 Step 3: Pre-screening with keyword filter...')
    passed, rejected = screen_job_list(full_jobs)
    print(f'   ✅ {len(passed)} passed  |  ❌ {len(rejected)} filtered out\n')

    if not passed:
        print('   All jobs filtered out. Sending empty digest.')
        send_digest(service, _empty_digest(len(rejected)))
        return

    if DRY_RUN:
        print('DRY RUN complete. Jobs that would be evaluated:')
        for j in passed:
            s = j.get('screen', {})
            print(f'  • {j.get("title","?")} @ {j.get("company","?")} [{s.get("archetype_fit","?")}]')
        return

    # ── 4. Groq evaluation ─────────────────────────────
    print('🤖 Step 4: Evaluating with Groq (Llama 3.3 70B)...')
    print(f'   Note: ~35s between calls to respect free tier limit\n')
    evaluated = []
    for i, job in enumerate(passed):
        title   = job.get('title', '?')
        company = job.get('company', '?')
        screen  = job.get('screen', {})
        print(f'   [{i+1}/{len(full_jobs)}] {title} @ {company}')

        try:
            ev    = evaluate_job(job,
                                 archetype_fit = screen.get('archetype_fit'))
            score = ev.get('fit_score', 0)
            tier  = ev.get('fit_tier', '?')
            pri   = ev.get('application_priority', '?')
            print(f'          Score: {score}/10 — {tier} — {pri}')
        except Exception as e:
            print(f'          ❌ Eval error: {e}')
            ev = {'fit_score': 0, 'is_worth_applying': False,
                  'fit_tier': 'Error', 'error': str(e)}

        job['evaluation'] = ev
        evaluated.append(job)

        # Log to Sheets for jobs meeting minimum score
        if ev.get('fit_score', 0) >= MIN_FIT_SCORE:
            log_job(job, ev)

    print(f'\n   Evaluation complete.\n')

    # ── 5. Send email digest ──────────────────────────────────
    print('📨 Step 5: Sending digest email...')
    results = [{'job': j, 'evaluation': j['evaluation']} for j in evaluated]
    html    = build_digest_html(results, filtered_count=len(rejected))

    send_digest(service, html)

    # ── Summary ───────────────────────────────────────────────
    worth   = [j for j in evaluated if j['evaluation'].get('is_worth_applying')]
    today_  = [j for j in evaluated
               if j['evaluation'].get('application_priority') == 'Apply today']

    print(f'\n{"="*55}')
    print(f'  ✅ Done — {date.today()}')
    print(f'  Emails read:       {len(emails)}')
    print(f'  Jobs extracted:    {len(unique)}')
    print(f'  After pre-screen:  {len(passed)}')
    print(f'  Evaluated:         {len(evaluated)}')
    print(f'  Worth applying:    {len(worth)}')
    print(f'  Apply TODAY:       {len(today_)}')
    print(f'{"="*55}\n')


def _empty_digest(filtered: int) -> str:
    return f"""<html><body style="font-family:Arial;max-width:600px;margin:auto;padding:20px;">
    <h2>Daily Job Digest — {date.today().strftime('%B %d, %Y')}</h2>
    <p>No relevant alerts today. {filtered} role(s) were filtered out by the keyword
    pre-screener (titles didn't match your target roles).</p>
    </body></html>"""


if __name__ == '__main__':
    if TEST_MODE:
        # Quick test — verifies Groq is working before running the full pipeline
        from evaluator import evaluate_job
        import json
        print('Running test evaluation with Groq...\n')
        #!!!--- Modify the below block to include a test case for code valdiation ---!!!
        result = evaluate_job({
            'title':       '[Your test job title]',
            'company':     '[Company name]',
            'location':    '[Remote / Hybrid / Onsite]',
            'description': '[Paste a sample job description here to test evaluation]',
            'job_url':     'https://linkedin.com/jobs/view/test',
        })
        print(json.dumps(result, indent=2))
    else:
        run_pipeline()