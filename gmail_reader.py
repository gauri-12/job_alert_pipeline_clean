# ─────────────────────────────────────────────────────────────────

"""
gmail_reader.py — Reads LinkedIn job alert emails from Gmail.
Extracts job URLs from the email HTML and marks emails as read.
"""
# ─────────────────────────────────────────────────────────────────

import os
import base64
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]


def get_gmail_service():
    """Authenticate and return a Gmail API service object."""
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as f:
            f.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def get_linkedin_alert_emails(service, max_results=20):
    """Fetch unread LinkedIn job alert emails from the last 24 hours."""
    query = 'from:jobalerts-noreply@linkedin.com is:unread newer_than:1d'
    results = service.users().messages().list(
        userId='me', q=query, maxResults=max_results
    ).execute()
    return results.get('messages', [])


def parse_jobs_from_email(service, message_id):
    """Extract job URLs from a LinkedIn alert email and mark it as read."""
    msg = service.users().messages().get(
        userId='me', id=message_id, format='full'
    ).execute()

    # Get HTML body
    html_content = _extract_html(msg['payload'])

    jobs = []
    if not html_content:
        return jobs

    # Find all LinkedIn job URLs in the email
    # Handles variants: /jobs/view/, /comm/jobs/view/, with or without www,
    # URL-encoded (%2F), and query strings after the job ID
    seen = set()
    patterns = [
        r'https?://(?:www\.)?linkedin\.com/comm/jobs/view/(\d+)',
        r'https?://(?:www\.)?linkedin\.com/jobs/view/(\d+)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, html_content):
            job_id = match.group(1)
            if job_id not in seen:
                seen.add(job_id)
                jobs.append({
                    'job_id': job_id,
                    'url': f'https://www.linkedin.com/jobs/view/{job_id}',
                    'title_hint': ''
                })

    # Also handle URL-encoded variants (%2F instead of /)
    if not jobs:
        for match in re.finditer(r'linkedin\.com(?:%2F|/)(?:comm(?:%2F|/))?jobs(?:%2F|/)view(?:%2F|/)(\d+)', html_content):
            job_id = match.group(1)
            if job_id not in seen:
                seen.add(job_id)
                jobs.append({
                    'job_id': job_id,
                    'url': f'https://www.linkedin.com/jobs/view/{job_id}',
                    'title_hint': ''
                })

    # Mark email as read
    service.users().messages().modify(
        userId='me', id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()

    return jobs


def _extract_html(payload):
    """Recursively extract HTML content from a Gmail message payload."""
    if payload.get('mimeType') == 'text/html':
        data = payload.get('body', {}).get('data', '')
        if data:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    for part in payload.get('parts', []):
        result = _extract_html(part)
        if result:
            return result

    return ''