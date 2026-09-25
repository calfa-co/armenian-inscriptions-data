#!/usr/bin/env python3
"""Goes in the DATA repository as .github/scripts/apply_correction.py

Reads a correction out of an issue body and writes corrections/<id>.json.

The contract with the interface is one fenced JSON block between
<!-- correction:begin --> and <!-- correction:end -->. Everything else in the
issue is prose for humans and is ignored.

This runs on a body that anyone on the internet can write, so it validates and
refuses rather than guessing: an unknown notice id, an unknown field, a crop
outside the page, or a transcription whose diplomatic notation is unbalanced all
stop the run with an explanation. The corpus is the product; a rejected issue
costs one comment, a wrong commit costs a reader's trust in every record.

Nothing here rewrites the machine extraction. notices.jsonl is untouched and
corrections/<id>.json only ever shadows it, so "what did the model produce"
stays answerable forever.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BLOCK = re.compile(r"<!--\s*correction:begin\s*-->(.*?)<!--\s*correction:end\s*-->", re.S)
FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)

EDITABLE = {"monument", "reference", "description", "transcription",
            "nb_lignes", "note", "page", "numero"}
STATUSES = {"unreviewed", "reviewed", "needs_attention"}
MAX_FIELD = 20000

# Diplomatic notation is the point of the corpus. A correction that leaves a
# bracket unclosed is almost always a copy-paste that lost its tail, and it is
# cheaper to reject it than to let it into the data and find it months later.
PAIRS = [("⎡", "⎤"), ("⎣", "⎦"), ("[", "]")]


def fail(msg: str) -> None:
    out(changed="false", message=f":x: **Not applied.** {msg}")
    sys.exit(0)          # a refusal is a normal outcome, not a broken workflow


def out(**kw) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        for k, v in kw.items():
            v = str(v).replace("\n", " ")
            fh.write(f"{k}={v}\n")


def main() -> int:
    body = os.environ.get("ISSUE_BODY") or ""
    user = os.environ.get("ISSUE_USER") or "unknown"
    num = os.environ.get("ISSUE_NUM") or "?"

    m = BLOCK.search(body)
    if not m:
        fail("no `correction:begin` / `correction:end` block found. Submit "
             "corrections through the proofreading interface so the block is "
             "written for you.")
    f = FENCE.search(m.group(1))
    raw = (f.group(1) if f else m.group(1)).strip()
    try:
        payload = json.loads(raw)
    except ValueError as e:
        fail(f"the correction block is not valid JSON ({e}).")

    nid = payload.get("id")
    if not isinstance(nid, str) or not re.fullmatch(r"[A-Za-z0-9_.԰-֏-]{1,64}", nid):
        fail("the correction has no usable notice id.")

    notices = Path("notices.jsonl")
    if not notices.exists():
        fail("notices.jsonl is missing from this repository.")
    notice = None
    for line in notices.read_text(encoding="utf-8").splitlines():
        if line.strip() and f'"id": "{nid}"' in line or f'"id":"{nid}"' in line:
            n = json.loads(line)
            if n.get("id") == nid:
                notice = n
                break
    if notice is None:
        fail(f"`{nid}` is not a notice in this corpus.")

    fields = payload.get("fields") or {}
    if not isinstance(fields, dict):
        fail("`fields` must be an object.")
    for k, v in fields.items():
        if k not in EDITABLE:
            fail(f"`{k}` is not a correctable field. Allowed: {', '.join(sorted(EDITABLE))}.")
        if not isinstance(v, str):
            fail(f"`{k}` must be text.")
        if len(v) > MAX_FIELD:
            fail(f"`{k}` is longer than {MAX_FIELD} characters.")
    tr = fields.get("transcription")
    if tr is not None:
        for op, cl in PAIRS:
            if tr.count(op) != tr.count(cl):
                fail(f"the transcription has {tr.count(op)} `{op}` and {tr.count(cl)} `{cl}`. "
                     "Diplomatic brackets must balance - check the value was not truncated.")

    crop = payload.get("crop")
    if crop is not None:
        if not isinstance(crop, dict) or "page" not in crop or "box" not in crop:
            fail("`crop` must have `page` and `box`.")
        if crop["page"] not in (notice.get("pages") or []):
            fail(f"`{crop['page']}` is not a page of notice `{nid}`.")
        box = crop["box"]
        if not (isinstance(box, list) and len(box) == 4 and all(isinstance(v, (int, float)) for v in box)):
            fail("`crop.box` must be four numbers [x1, y1, x2, y2].")
        geo = (notice.get("page_geometry") or {}).get(crop["page"])
        if geo:
            x1, y1, x2, y2 = box
            if not (0 <= x1 < x2 <= geo["width"] and 0 <= y1 < y2 <= geo["height"]):
                fail(f"`crop.box` {box} falls outside the {geo['width']}x{geo['height']} page.")
        crop = {"page": crop["page"], "box": [int(round(v)) for v in box]}

    status = payload.get("review_status")
    if status is not None and status not in STATUSES:
        fail(f"`review_status` must be one of {', '.join(sorted(STATUSES))}.")

    if not fields and crop is None and status is None:
        fail("the correction is empty.")

    # Merge onto whatever is already recorded, so two issues touching different
    # fields of one notice both survive.
    path = Path("corrections") / f"{nid}.json"
    path.parent.mkdir(exist_ok=True)
    rec = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"id": nid, "fields": {}}
    rec.setdefault("fields", {}).update(fields)
    if crop is not None:
        rec["crop"] = crop
        rec["crop_status"] = "corrected"
    if status:
        rec["review_status"] = status
    rec["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rec["updated_by"] = user
    rec["source_issue"] = int(num) if str(num).isdigit() else num
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")

    what = ", ".join(sorted(fields)) + (", crop" if crop else "")
    out(changed="true",
        summary=f"correction: {nid} ({what})",
        message=f":white_check_mark: Applied to `corrections/{nid}.json` - **{what}**, "
                f"credited to @{user}. The machine extraction is unchanged and "
                f"remains visible beside your correction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
