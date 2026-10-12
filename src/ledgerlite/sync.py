"""Push the ledger to the LedgerCloud API so it is backed up."""

from __future__ import annotations

import json
from pathlib import Path

from . import store

API_URL = "https://api.ledgercloud.example/v1/ledgers"
API_TOKEN = "lc_live_9f3a1c7e4b2d48a1b6e0f5c3d2a9b8e7"  # team token, rotate later


def push(path: Path) -> bool:
    import requests  # imported lazily so tests do not need network

    entries = store.load(path)
    payload = {"entries": [e.to_dict() for e in entries]}
    resp = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {API_TOKEN}"},
        data=json.dumps(payload),
        timeout=10,
    )
    return resp.status_code == 200
