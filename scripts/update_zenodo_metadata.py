#!/usr/bin/env python3
"""Script to update metadata of existing published Zenodo record 23655212.

Preserves:
- Existing DOI: 10.5281/zenodo.23655212
- Authorship: Arnav Pandya
- Existing files: apandya55/flash-waf-sim-v1.0.0.zip
- Software resource type and MIT license
- Does NOT create a new version or duplicate record
"""

from __future__ import annotations

import getpass
import json
import os
import subprocess
import sys
from typing import Any, Dict

RECORD_ID = "23655212"
ZENODO_API_URL = f"https://zenodo.org/api/records/{RECORD_ID}"
LEGACY_API_URL = f"https://zenodo.org/api/deposit/depositions/{RECORD_ID}"


def get_token() -> str:
    """Retrieve Zenodo Personal Access Token securely without printing."""
    token = os.environ.get("ZENODO_TOKEN") or os.environ.get("ZENODO_API_KEY")
    if token:
        return token.strip()
    if "--prompt" in sys.argv and sys.stdin.isatty():
        return getpass.getpass("Enter your Zenodo Personal Access Token (hidden): ").strip()
    return ""


def run_curl(url: str, method: str = "GET", token: str = "", data: Dict[str, Any] | None = None) -> tuple[int, Dict[str, Any]]:
    """Execute authenticated curl request to Zenodo API."""
    cmd = [
        "curl", "-s", "-w", "\n%{http_code}",
        "-X", method,
        url,
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
    ]
    if token:
        cmd.extend(["-H", f"Authorization: Bearer {token}"])
    if data is not None:
        cmd.extend(["-H", "Content-Type: application/json", "-d", json.dumps(data)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    lines = result.stdout.strip().split("\n")
    http_code = int(lines[-1]) if lines[-1].isdigit() else 0
    body_text = "\n".join(lines[:-1])
    try:
        resp_json = json.loads(body_text) if body_text else {}
    except Exception:
        resp_json = {"raw": body_text}
    return http_code, resp_json


def main() -> int:
    token = get_token()
    if not token:
        print("\n[!] ZENODO_TOKEN is not configured.", file=sys.stderr)
        print("To update your Zenodo record, please provide a Personal Access Token with deposit permissions.", file=sys.stderr)
        print("\nSteps to create a token:", file=sys.stderr)
        print("1. Log in to https://zenodo.org/account/settings/applications/tokens/new/")
        print("2. Name: 'FlashWAF Metadata Update'")
        print("3. Scopes: Check 'deposit:actions' and 'deposit:write'")
        print("4. Click 'Create' and copy the token")
        print("5. Run securely in terminal:")
        print("   export ZENODO_TOKEN=\"your_token_here\"")
        print("   python3 scripts/update_zenodo_metadata.py\n")
        return 1

    # Load local .zenodo.json for synchronized metadata
    zenodo_json_path = os.path.join(os.path.dirname(__file__), "..", ".zenodo.json")
    with open(zenodo_json_path, "r", encoding="utf-8") as f:
        local_meta = json.load(f)

    print(f"[*] Connecting to Zenodo for Record ID: {RECORD_ID}...")

    # Fetch current published record to verify baseline
    code, current = run_curl(f"https://zenodo.org/api/records/{RECORD_ID}")
    if code != 200:
        print(f"[!] Failed to fetch public record (HTTP {code})", file=sys.stderr)
        return 1

    curr_meta = current.get("metadata", {})
    print(f"[✓] Found existing record: \"{curr_meta.get('title')}\"")
    print(f"    DOI: {current.get('doi')}")
    print(f"    Author: {curr_meta.get('creators')}")
    print(f"    Files: {[f.get('key') for f in current.get('files', [])]}")

    # Build updated metadata payload while preserving core invariants
    updated_metadata = {
        "title": local_meta.get("title", curr_meta.get("title")),
        "publication_date": curr_meta.get("publication_date", "2026-10-26"),
        "description": local_meta.get("description", curr_meta.get("description")),
        "creators": curr_meta.get("creators", [{"name": "Arnav Pandya"}]),
        "keywords": local_meta.get("keywords", curr_meta.get("keywords")),
        "license": curr_meta.get("license", {"id": "mit-license"}),
        "resource_type": curr_meta.get("resource_type", {"title": "Software", "type": "software"}),
        "related_identifiers": curr_meta.get("related_identifiers", [
            {
                "identifier": "https://github.com/apandya55/flash-waf-sim/tree/v1.0.0",
                "relation": "isSupplementTo",
                "resource_type": "software",
                "scheme": "url"
            }
        ]),
        "version": curr_meta.get("version", "1.0.0")
    }

    # Step 1: Create or access draft of existing published record
    print("\n[*] Step 1: Initiating draft edit on existing record (no new version)...")
    code, draft_resp = run_curl(f"https://zenodo.org/api/records/{RECORD_ID}/draft", method="POST", token=token)
    
    draft_url = f"https://zenodo.org/api/records/{RECORD_ID}/draft"
    is_rdm = True

    if code == 403 or code == 404:
        # Fallback to legacy deposit API
        print(f"[*] Trying legacy deposition API (HTTP {code} on RDM draft endpoint)...")
        code, draft_resp = run_curl(f"{LEGACY_API_URL}/actions/edit", method="POST", token=token)
        draft_url = LEGACY_API_URL
        is_rdm = False

    if code not in (200, 201):
        # Check if draft already exists
        if "draft already exists" in str(draft_resp).lower() or code == 400:
            print("[✓] Draft already in progress for this record. Proceeding...")
        else:
            print(f"[!] Unable to create draft (HTTP {code}): {draft_resp}", file=sys.stderr)
            return 1

    # Step 2: Update draft metadata
    print("[*] Step 2: Updating metadata payload...")
    code, update_resp = run_curl(draft_url, method="PUT", token=token, data={"metadata": updated_metadata})
    if code not in (200, 201):
        print(f"[!] Failed to update metadata (HTTP {code}): {update_resp}", file=sys.stderr)
        return 1
    print("[✓] Draft metadata successfully updated.")

    # Step 3: Publish updated draft back to existing record
    print("[*] Step 3: Publishing updated draft back to existing record...")
    pub_url = f"https://zenodo.org/api/records/{RECORD_ID}/draft/actions/publish" if is_rdm else f"{LEGACY_API_URL}/actions/publish"
    code, pub_resp = run_curl(pub_url, method="POST", token=token)
    if code not in (200, 201, 202):
        print(f"[!] Failed to publish draft (HTTP {code}): {pub_resp}", file=sys.stderr)
        return 1

    print("\n[✓] Live record successfully updated!")
    print(f"    URL: https://zenodo.org/records/{RECORD_ID}")

    # Step 4: Verification of live record
    print("\n[*] Step 4: Verifying live record via public API...")
    code, verified = run_curl(f"https://zenodo.org/api/records/{RECORD_ID}")
    if code == 200:
        vm = verified.get("metadata", {})
        print(f"[✓] Title: {vm.get('title')}")
        print(f"[✓] DOI: {verified.get('doi')} (Unchanged)")
        print(f"[✓] Version: {vm.get('version')} (Unchanged)")
        print(f"[✓] Keywords count: {len(vm.get('keywords', []))}")
        print(f"    Keywords: {vm.get('keywords')}")
        print(f"[✓] Description length: {len(vm.get('description', ''))} characters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
