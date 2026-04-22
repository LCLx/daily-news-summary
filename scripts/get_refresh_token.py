#!/usr/bin/env python3
"""
One-shot script to get a Gmail refresh token via Google OAuth2.

Prerequisite: in Google Cloud Console, add `http://localhost` to the
OAuth client's Authorized redirect URIs (no port, no trailing slash).

Usage:
    uv run scripts/get_refresh_token.py
"""

import os
import sys
import urllib.parse
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import requests
from core.config import GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET

REDIRECT_URI = "http://localhost"
SCOPE = "https://www.googleapis.com/auth/gmail.send"


def main():
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET:
        print("GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET not set in .env")
        sys.exit(1)

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": GMAIL_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    })

    print("Opening browser for authorization...\n")
    print(f"If it doesn't open, visit manually:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print("After granting access, the browser will redirect to http://localhost/?code=...")
    print("The page will show \"site can't be reached\" — that's expected.\n")
    print("Paste the full redirect URL (or just the code=xxx part) below:")
    pasted = input("\n> ").strip()

    if "code=" in pasted:
        code = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query).get("code", [None])[0]
        if not code:
            code = pasted.split("code=", 1)[1].split("&", 1)[0]
    else:
        code = pasted

    if not code:
        print("Could not parse authorization code")
        sys.exit(1)

    print("\nExchanging code for refresh token...")
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": GMAIL_CLIENT_ID,
        "client_secret": GMAIL_CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    if not resp.ok:
        print(f"Token exchange failed ({resp.status_code}): {resp.text}")
        sys.exit(1)

    token = resp.json().get("refresh_token")
    if not token:
        print(f"No refresh_token in response: {resp.json()}")
        sys.exit(1)

    print("\nRefresh token acquired. Replace the value in .env:\n")
    print(f"GMAIL_REFRESH_TOKEN={token}")


if __name__ == "__main__":
    main()
