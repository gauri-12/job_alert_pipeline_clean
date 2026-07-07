# ─────────────────────────────────────────────────────────────────

"""
sheets_logger.py — Logs job evaluations to Google Sheets.
Uses the same OAuth credentials as Gmail (no separate service account needed).
"""

"""
The order of columns in the Google Sheet can be controlled using HEADERS on line 26 and row on line 71. Reorder the output in whichever order you like but ensure the order of these 
columns remain the same under both.

"""

# ─────────────────────────────────────────────────────────────────

import os
import gspread
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '')

# Column headers — paste these into Row 1 of your Google Sheet manually
HEADERS = [
    'Date', 'Job Title', 'Company', 'Location',
    'Fit Score', 'Fit Tier', 'Fit Summary',
    'Matching Strengths', 'Skill Gaps', 'Resume Updates',
    'Comp Flag', 'Location Flag',
    'Seniority Flag', 'Apply Priority', 'Approach', 'Job URL'
]


def get_sheets_client():
    """Return an authenticated gspread client using the existing Gmail token."""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/gmail.modify',
    ]
    creds = Credentials.from_authorized_user_file('token.json', scopes)
    return gspread.authorize(creds)


def ensure_headers(sheet):
    """Add header row if the sheet is empty."""
    if sheet.row_count == 0 or sheet.cell(1, 1).value != 'Date':
        sheet.insert_row(HEADERS, 1)


def log_job(job: dict, evaluation: dict):
    """Append one evaluated job as a new row in the Google Sheet."""
    if not SHEET_ID:
        print('   ⚠️  GOOGLE_SHEET_ID not set — skipping Sheets log')
        return

    try:
        client = get_sheets_client()
        sheet = client.open_by_key(SHEET_ID).sheet1
        ensure_headers(sheet)

        # Format resume updates as readable text
        updates = evaluation.get('resume_updates_needed', [])
        updates_text = '; '.join(
            f"{u.get('section','')}: {u.get('suggestion','')}"
            for u in updates
        ) if updates else ''

        from datetime import date
        row = [
        str(date.today()),                                    # Date
        job.get('title', ''),                                 # Job Title
        job.get('company', ''),                               # Company
        job.get('location', ''),                              # Location
        evaluation.get('fit_score', ''),                      # Fit Score
        evaluation.get('fit_tier', ''),                       # Fit Tier
        evaluation.get('fit_summary', ''),                    # Fit Summary
        ', '.join(evaluation.get('matching_strengths', [])),  # Matching Strengths
        ', '.join(evaluation.get('skill_gaps', [])),          # Skill Gaps
        updates_text,                                         # Resume Updates
        evaluation.get('compensation_flag', ''),              # Comp Flag
        evaluation.get('location_flag', ''),                  # Location Flag
        evaluation.get('seniority_flag', ''),                 # Seniority Flag
        evaluation.get('application_priority', ''),           # Apply Priority
        evaluation.get('recommended_approach', ''),           # Approach
        job.get('job_url', ''),                               # Job URL
        ]

        
        sheet.append_row(row)

    except Exception as e:
        print(f'   ⚠️  Sheets error: {e}')
