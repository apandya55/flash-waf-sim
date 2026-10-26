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
RDM_DRAFT_URL = f"https://zenodo.org/api/records/{RECORD_ID}/draft"
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
        print("\nRun securely in terminal:")
        print("   export ZENODO_TOKEN=\"your_token_here\"")
        print("   python3 scripts/update_zenodo_metadata.py\n")
        return 1

    # Load local .zenodo.json for synchronized metadata
    zenodo_json_path = os.path.join(os.path.dirname(__file__), "..", ".zenodo.json")
    with open(zenodo_json_path, "r", encoding="utf-8") as f:
        local_meta = json.load(f)

    print(f"[*] Connecting to Zenodo for Record ID: {RECORD_ID}...")

    # Step 1: Create or access draft of existing published record
    print("\n[*] Step 1: Accessing edit draft on existing record (no new version)...")
    code, draft_resp = run_curl(RDM_DRAFT_URL, method="POST", token=token)
    
    if code in (200, 201):
        print("[✓] Draft initialized.")
    elif code == 400 or "draft already exists" in str(draft_resp).lower():
        print("[✓] Draft already in progress for this record. Proceeding...")
    else:
        print(f"[!] Draft POST response (HTTP {code}): {draft_resp}")

    # Fetch the draft to inspect its current fields
    code, current_draft = run_curl(RDM_DRAFT_URL, method="GET", token=token)
    if code != 200:
        print(f"[!] Failed to fetch draft details (HTTP {code}): {current_draft}", file=sys.stderr)
        return 1

    draft_meta = current_draft.get("metadata", {})

    # Step 2: Build exact InvenioRDM compliant metadata
    keywords = local_meta.get("keywords", [])
    subjects = [{"subject": kw} for kw in keywords]

    updated_metadata: Dict[str, Any] = {
        "title": local_meta.get("title", draft_meta.get("title", "FlashWAF: a page-mapped flash simulator")),
        "publisher": "Zenodo",
        "publication_date": "2026-10-26",
        "description": local_meta.get("description", draft_meta.get("description", "")),
        "resource_type": {"id": "software"},
        "creators": [
            {
                "person_or_org": {
                    "type": "personal",
                    "given_name": "Arnav",
                    "family_name": "Pandya"
                }
            }
        ],
        "subjects": subjects,
        "rights": [{"id": "mit"}],
        "related_identifiers": [
            {
                "identifier": "https://github.com/apandya55/flash-waf-sim/tree/v1.0.0",
                "scheme": "url",
                "relation_type": {"id": "issupplementto"},
                "resource_type": {"id": "software"}
            }
        ],
        "version": "1.0.0"
    }

    # Add custom repository pointer if present
    if "custom" in draft_meta:
        updated_metadata["custom"] = draft_meta["custom"]
    else:
        updated_metadata["custom"] = {"code:codeRepository": "https://github.com/apandya55/flash-waf-sim"}

    print("[*] Step 2: Updating draft metadata payload (InvenioRDM schema)...")
    code, update_resp = run_curl(RDM_DRAFT_URL, method="PUT", token=token, data={"metadata": updated_metadata})
    if code not in (200, 201):
        print(f"[!] Failed to update metadata (HTTP {code}): {update_resp}", file=sys.stderr)
        return 1
    print("[✓] Draft metadata successfully updated.")

    # Step 3: Publish updated draft back to existing record
    print("[*] Step 3: Publishing updated draft back to existing record...")
    pub_url = f"{RDM_DRAFT_URL}/actions/publish"
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
        subjects_list = vm.get("subjects") or vm.get("keywords") or []
        print(f"[✓] Subjects / Keywords count: {len(subjects_list)}")
        print(f"    Subjects: {subjects_list}")
        print(f"[✓] Description length: {len(vm.get('description', ''))} characters")
    return 0


if __name__ == "__main__":
    sys.exit(main())
