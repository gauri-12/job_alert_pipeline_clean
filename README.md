# Job Alert Pipeline

An automated daily pipeline that reads your LinkedIn job alert emails, fetches full job descriptions, evaluates each role against your resume using an LLM, logs matches to Google Sheets, and emails you a formatted digest — all for free, running on GitHub Actions every night.

**Powered by:** Gmail API · LinkedIn public API · Groq (Llama 3.3 70B) · Google Sheets · GitHub Actions

---

## How it works

```
Gmail (LinkedIn alert emails)
        ↓
  gmail_reader.py   — reads unread LinkedIn alert emails, extracts job URLs
        ↓
  job_fetcher.py    — fetches full job descriptions from LinkedIn's public API
        ↓
  pre_screener.py   — keyword filter (free, no API calls) drops irrelevant roles
        ↓
  evaluator.py      — Groq scores each job against your resume (1–10)
        ↓
  sheets_logger.py  — logs results to Google Sheets (score ≥ MIN_FIT_SCORE)
        ↓
  digest_sender.py  — sends you an HTML email digest with all results

config.py ──────────→ pre_screener.py  (keywords, archetypes, salary floor)
          ──────────→ evaluator.py      (profile, scoring instructions, calibration)
```

GitHub Actions runs this every night at midnight UTC via `daily_pipeline.yml`.

**To use this pipeline, there are only 3 places to update:**
- `config.py` — the only file with personal settings (profile, keywords, scoring instructions, salary floor). Fill this in before your first run.
- `pre_screener.py` — update the test cases at the bottom of the file to match your own roles before running a local test.
- `main.py` — update the test job block (lines 182–188) with a sample role before running `python main.py --test`.

---

## Prerequisites

Before you start, you'll need accounts on these free services:

- **Google account** (Gmail) with LinkedIn job alert emails set up
- **Google Cloud** account (free) — for the Gmail and Sheets APIs
- **Groq** account (free) — for LLM job evaluation at [console.groq.com](https://console.groq.com)
- **GitHub** account — for hosting the code and running the automation

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/job-alert-pipeline.git
cd job-alert-pipeline
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up the Gmail and Sheets API (Google Cloud)

This is the most involved step — it only needs to be done once.

**a. Create a Google Cloud project**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click "New Project", name it anything (e.g. `job-pipeline`), click Create

**b. Enable the APIs**
1. In the left sidebar go to "APIs & Services" → "Library"
2. Search for and enable **Gmail API**
3. Search for and enable **Google Sheets API**
4. Search for and enable **Google Drive API**

**c. Create OAuth credentials**
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted to configure the consent screen: choose "External", fill in an app name, add your Gmail address as a test user, and save
4. Application type: **Desktop app**
5. Click Create — download the JSON file
6. Save it as `credentials.json` in the project root (it's gitignored)

**d. Generate your token**

Run this once locally — it will open a browser window asking you to log in and grant access:

```bash
python -c "from gmail_reader import get_gmail_service; get_gmail_service()"
```

After you click "Allow" in the browser, a `token.json` file is created in the project root. This is your OAuth token. **Keep it safe — treat it like a password.**

### 4. Set up Groq (free LLM API)

1. Sign up at [console.groq.com](https://console.groq.com) — free, no credit card needed
2. Go to "API Keys" → create a new key
3. Copy the key — you'll add it to `.env` in the next step

### 5. Set up Google Sheets

1. Create a new Google Sheet at [sheets.google.com](https://sheets.google.com)
2. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/THIS_PART_HERE/edit`
3. The pipeline will auto-create headers on the first run — no manual setup needed

### 6. Create your local `.env` file

Create a `.env` file in the project root (it's gitignored):

```env
GROQ_API_KEY=your_groq_api_key_here
GMAIL_USER=your.email@gmail.com
GOOGLE_SHEET_ID=your_google_sheet_id_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_CALL_DELAY=35
MIN_FIT_SCORE=6
```

`GROQ_CALL_DELAY=35` keeps API calls within Groq's free tier rate limit (6,000 tokens/minute). Don't lower it unless you're on a paid plan.

`MIN_FIT_SCORE` controls which jobs get logged to Sheets. Jobs scoring below this threshold are still included in the email digest but not saved to the spreadsheet.

### 7. Customise `config.py`

Open `config.py` — this is the **only file you need to edit** to personalise the pipeline. Fill in:
- `SYSTEM_ROLE` — tailor the LLM persona to your field
- `YOUR_PROFILE` — your target roles, compensation target, location, and top strengths
- `EVALUATION_INSTRUCTIONS` — the scoring criteria for your roles
- `CALIBRATION_EXAMPLES` — 2–3 concrete examples to anchor the score scale
- `POSITIVE_KEYWORDS` / `NEGATIVE_KEYWORDS` — keywords to pass or filter jobs
- `SENIORITY_BOOST` — seniority terms relevant to your target level
- `ROLE_ARCHETYPES` — your primary, secondary, and adjacent role types
- `COMP_MINIMUM_USD` — your salary floor used in pre-screening and evaluation

### 8. Add your resume

Fill in the file called `resume.txt` in the project root and paste your resume content in plain text. This file is gitignored and will never be committed.

---

## Running locally

```bash
# Full run
python main.py

# Dry run — reads emails and pre-screens jobs, but skips Groq and Sheets
python main.py --dry-run

# Test mode — runs one sample evaluation to verify Groq is connected
python main.py --test
```

---

## GitHub Actions setup (automated nightly runs)

Once you've tested locally, you can automate the pipeline to run every night.

### Add secrets to your GitHub repo

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret** and add each of these:

| Secret name | Value |
|---|---|
| `GOOGLE_CREDENTIALS` | Paste the full contents of `credentials.json` |
| `GOOGLE_TOKEN` | Paste the full contents of `token.json` |
| `GROQ_API_KEY` | Your Groq API key |
| `GMAIL_USER` | Your Gmail address |
| `GOOGLE_SHEET_ID` | Your Google Sheet ID |

### Push the workflow

The workflow file is already at `.github/workflows/daily_pipeline.yml`. Push it to GitHub and the pipeline will run automatically at midnight UTC every night. You can also trigger it manually from the Actions tab.

### Keeping your token fresh

The Gmail OAuth token expires periodically. When it does, the pipeline will fail with `invalid_grant: Token has been expired or revoked`. To fix it:

1. Re-run the local auth step: `python -c "from gmail_reader import get_gmail_service; get_gmail_service()"`
2. Open the newly generated `token.json`
3. Go to GitHub → Settings → Secrets → update the `GOOGLE_TOKEN` secret with the new contents

---

## Customising for your job search

**All personal settings** — Edit `config.py` (the only file you need to touch):
- `POSITIVE_KEYWORDS` / `NEGATIVE_KEYWORDS` — keywords to pass or filter jobs
- `ROLE_ARCHETYPES` — your primary/secondary/adjacent role types
- `YOUR_PROFILE` — target roles, compensation, location, and superpowers
- `EVALUATION_INSTRUCTIONS` / `CALIBRATION_EXAMPLES` — scoring logic tailored to your field
- `COMP_MINIMUM_USD` — salary floor for pre-screening

**Schedule** — Edit `.github/workflows/daily_pipeline.yml`:
- The cron `0 0 * * *` runs at midnight UTC (5 PM PST). Change to whatever time works for you.
- Cron reference: `0 17 * * 1-5` would run at 5 PM UTC on weekdays only.

**Minimum fit score** — Set `MIN_FIT_SCORE` in `.env` (default: 6). Jobs at or above this score get logged to Google Sheets.

---

## Files overview

```
├── config.py             # ⭐ The only file you need to edit — all personal settings
├── main.py               # Pipeline orchestrator
├── gmail_reader.py       # Reads LinkedIn alert emails from Gmail
├── job_fetcher.py        # Fetches full job descriptions from LinkedIn
├── pre_screener.py       # Fast keyword filter (no API cost)
├── evaluator.py          # LLM job evaluation via Groq
├── sheets_logger.py      # Logs results to Google Sheets
├── digest_sender.py      # Sends HTML email digest
├── resume.txt            # Fill in with your resume file
├── requirements.txt      # Python dependencies
│
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml   # GitHub Actions workflow
│
└── .gitignore            # Keeps credentials and personal files off GitHub

```

**Files that are gitignored (never committed):**
- `credentials.json` — your Google OAuth client secret
- `token.json` — your OAuth access token
- `.env` — your API keys and config
- `resume.txt` — your resume content

---

## Troubleshooting

**`invalid_grant: Token has been expired or revoked`**
Your Gmail OAuth token has expired. Re-run the local auth step and update the `GOOGLE_TOKEN` GitHub secret. See the "Keeping your token fresh" section above.

**`resume.txt not found`**
Create the file in the project root and paste your resume in plain text: `touch resume.txt`

**No emails found**
Make sure you have LinkedIn job alert emails set up. In LinkedIn, go to Jobs → Job Alerts and create alerts for your target roles. The pipeline looks for emails from `jobalerts-noreply@linkedin.com` that arrived in the last 24 hours and are unread.

**Groq rate limit errors**
Increase `GROQ_CALL_DELAY` in `.env`. The free tier allows 6,000 tokens/minute; 35 seconds between calls is usually safe.

**Jobs not appearing in Google Sheets**
Check that `GOOGLE_SHEET_ID` is correct and that `MIN_FIT_SCORE` isn't set too high. Also confirm the Google Sheets API is enabled in your Cloud project.
