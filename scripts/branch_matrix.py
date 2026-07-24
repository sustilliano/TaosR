#!/usr/bin/env python3
"""Branch-comparison matrix: every remote branch vs. our base branch.

For each branch B on ``--remote`` (default ``origin``), compares B against
``--base`` (default ``origin/robotics-edition``) and reports:

* merge-base sha (or "unrelated/deep" if none can be found — e.g. an
  orphan branch such as ``cla-signatures``)
* commits-ahead / commits-behind the base
* whether B is already fully merged into the base (no unique commits)
* files-changed / insertions / deletions (``git diff --shortstat base...B``)
* the top changed top-level directories (a cheap proxy for "what area of
  the tree this branch touches")
* the branch's newest commit subject/author/date
* a coarse "kind" heuristic from the branch name (dependabot, release,
  sync, exec-scratch, docs, feat, fix, test, chore, other) to make the
  shortlisting pass in the design doc easier

This is a **read-only, analysis-only** tool. It does not fetch, merge,
push, or otherwise mutate the repository — run ``git fetch`` yourself
first (see ``docs/design/branch-matrix.md`` for the exact incantation
used to build the local ref set this was run against).

Requires the branches to be present as local refs (e.g.
``refs/remotes/origin/<branch>``) with enough history that
``git merge-base`` can resolve against ``--base``. A full
``git fetch origin --unshallow`` is the simplest way to guarantee that.

Usage:
    python3 scripts/branch_matrix.py
    python3 scripts/branch_matrix.py --base origin/robotics-edition \\
        --remote origin \\
        --json-out reports/branch-matrix.json \\
        --md-out reports/branch-matrix.md

Output is deterministic given the same repo state: branches are read via
``git for-each-ref`` (already lexicographic) and every sort is stable
with a branch-name tiebreak.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def run(args: list[str], check: bool = True) -> str:
    """Run a git command from the repo root, return stripped stdout."""
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def try_run(args: list[str]) -> str | None:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def list_remote_branches(remote: str) -> list[str]:
    """Short branch names under refs/remotes/<remote>/, HEAD excluded."""
    out = run(
        [
            "for-each-ref",
            f"refs/remotes/{remote}",
            "--format=%(refname:short)",
        ]
    )
    names = []
    prefix = f"{remote}/"
    for line in out.splitlines():
        if not line.startswith(prefix):
            continue
        short = line[len(prefix):]
        if short == "HEAD":
            continue
        names.append(short)
    return sorted(names)


def classify_kind(branch: str) -> str:
    b = branch.lower()
    if b.startswith("dependabot/"):
        return "dependabot"
    if b.startswith("exec/tsk-"):
        return "exec-scratch"
    if b.startswith("release/"):
        return "release"
    if b.startswith("sync/"):
        return "sync"
    if b.startswith(("docs/", "review/docs")):
        return "docs"
    if b.startswith("feat/"):
        return "feat"
    if b.startswith("fix/"):
        return "fix"
    if b.startswith("test/"):
        return "test"
    if b.startswith(("chore/", "spec/", "gauge/", "perf/", "verify/")):
        return "chore"
    return "other"


def parse_shortstat(text: str) -> dict:
    """Parse 'N files changed, X insertions(+), Y deletions(-)' loosely."""
    files = insertions = deletions = 0
    if not text:
        return {"files_changed": 0, "insertions": 0, "deletions": 0}
    for part in text.split(","):
        part = part.strip()
        if "file" in part:
            files = int(part.split()[0])
        elif "insertion" in part:
            insertions = int(part.split()[0])
        elif "deletion" in part:
            deletions = int(part.split()[0])
    return {"files_changed": files, "insertions": insertions, "deletions": deletions}


def top_dirs(names: list[str], depth: int = 1, limit: int = 5) -> list[dict]:
    buckets: Counter[str] = Counter()
    for n in names:
        if not n:
            continue
        parts = n.split("/")
        if len(parts) == 1:
            bucket = parts[0]
        else:
            bucket = "/".join(parts[:depth])
        buckets[bucket] += 1
    return [
        {"dir": d, "files": c}
        for d, c in sorted(buckets.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    ]


def analyze_branch(branch: str, remote: str, base: str) -> dict:
    ref = f"{remote}/{branch}"
    entry: dict = {
        "branch": branch,
        "ref": ref,
        "kind": classify_kind(branch),
    }

    head_sha = try_run(["rev-parse", ref])
    entry["head_sha"] = head_sha[:12] if head_sha else None

    subject = try_run(["log", "-1", "--format=%s", ref])
    author = try_run(["log", "-1", "--format=%an", ref])
    date = try_run(["log", "-1", "--format=%cI", ref])
    entry["last_subject"] = subject or ""
    entry["last_author"] = author or ""
    entry["last_date"] = date or ""

    if ref == base or head_sha == try_run(["rev-parse", base]):
        entry.update(
            {
                "merge_base": entry["head_sha"],
                "resolvable": True,
                "ahead": 0,
                "behind": 0,
                "merged": True,
                "files_changed": 0,
                "insertions": 0,
                "deletions": 0,
                "top_dirs": [],
                "absorbed_files": 0,
                "fully_absorbed": False,
                "note": "is the base branch itself",
            }
        )
        return entry

    mb = try_run(["merge-base", base, ref])
    if not mb:
        entry.update(
            {
                "merge_base": None,
                "resolvable": False,
                "ahead": None,
                "behind": None,
                "merged": False,
                "files_changed": None,
                "insertions": None,
                "deletions": None,
                "top_dirs": [],
                "note": "unrelated/deep — no common ancestor found",
            }
        )
        return entry

    entry["merge_base"] = mb[:12]
    entry["resolvable"] = True

    ahead_out = try_run(["rev-list", "--count", f"{base}..{ref}"])
    behind_out = try_run(["rev-list", "--count", f"{ref}..{base}"])
    ahead = int(ahead_out) if ahead_out else 0
    behind = int(behind_out) if behind_out else 0
    entry["ahead"] = ahead
    entry["behind"] = behind
    entry["merged"] = ahead == 0

    shortstat = try_run(["diff", "--shortstat", f"{mb}...{ref}"]) or ""
    entry.update(parse_shortstat(shortstat))

    names_out = try_run(["diff", "--name-only", f"{mb}...{ref}"]) or ""
    names = [n for n in names_out.splitlines() if n]
    entry["top_dirs"] = top_dirs(names)

    # Redundancy check: of the files this branch touches (relative to its
    # own merge-base), how many are BYTE-IDENTICAL between our current base
    # tip and the branch tip? A branch can show ahead>0 / merged=False by
    # commit ancestry alone yet still be fully redundant if the same content
    # landed on our side through a different commit (squash-merge, rebase,
    # independent reimplementation, etc). absorbed_files == files_changed
    # means "nothing left to adopt here" even though git doesn't consider
    # it merged.
    absorbed_files = 0
    if names:
        still_diff = try_run(["diff", "--name-only", base, ref, "--", *names])
        changed_of_touched = len(still_diff.splitlines()) if still_diff else 0
        absorbed_files = len(names) - changed_of_touched
    entry["absorbed_files"] = absorbed_files
    entry["fully_absorbed"] = bool(names) and absorbed_files == len(names)
    entry["note"] = "fully absorbed — identical content already present on base" if entry["fully_absorbed"] else ""

    return entry


def sort_key(entry: dict):
    # Most-ahead first, then most-changed, then branch name for stability.
    # Unresolved entries (ahead=None) sort to the bottom.
    ahead = entry["ahead"] if entry["ahead"] is not None else -1
    files = entry["files_changed"] if entry["files_changed"] is not None else -1
    return (-ahead, -files, entry["branch"])


def render_markdown(base: str, remote: str, entries: list[dict]) -> str:
    now = datetime.now(timezone.utc).isoformat()
    lines = [
        "# Branch matrix",
        "",
        f"Generated {now} — {len(entries)} branches on `{remote}` vs. base `{base}`.",
        "",
        "| Branch | Kind | Ahead | Behind | Merged | Absorbed | Files | +/- | Top dirs | Last commit |",
        "|---|---|---:|---:|---|---|---:|---|---|---|",
    ]
    for e in entries:
        if not e["resolvable"]:
            lines.append(
                f"| `{e['branch']}` | {e['kind']} | — | — | — | — | — | — | "
                f"unrelated/deep | {e['last_subject'].replace('|', chr(92)+'|')} |"
            )
            continue
        dirs = ", ".join(f"{d['dir']} ({d['files']})" for d in e["top_dirs"]) or "—"
        pm = f"+{e['insertions']}/-{e['deletions']}"
        merged = "yes" if e["merged"] else "no"
        if e["merged"]:
            absorbed = "—"
        elif e["fully_absorbed"]:
            absorbed = "yes"
        elif e.get("files_changed"):
            absorbed = f"{e['absorbed_files']}/{e['files_changed']}"
        else:
            absorbed = "—"
        subject = e["last_subject"].replace("|", "\\|")
        lines.append(
            f"| `{e['branch']}` | {e['kind']} | {e['ahead']} | {e['behind']} | "
            f"{merged} | {absorbed} | {e['files_changed']} | {pm} | {dirs} | {subject} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument(
        "--base",
        default="origin/robotics-edition",
        help="ref to compare every branch against (default: origin/robotics-edition)",
    )
    parser.add_argument(
        "--remote",
        default="origin",
        help="remote whose branches to enumerate (default: origin)",
    )
    parser.add_argument(
        "--json-out",
        default="reports/branch-matrix.json",
        help="path to write JSON output (default: reports/branch-matrix.json)",
    )
    parser.add_argument(
        "--md-out",
        default="reports/branch-matrix.md",
        help="path to write Markdown table output (default: reports/branch-matrix.md)",
    )
    parser.add_argument(
        "--branch",
        action="append",
        dest="only_branches",
        help="limit to this branch (repeatable); default is all branches on --remote",
    )
    args = parser.parse_args(argv)

    branches = args.only_branches or list_remote_branches(args.remote)

    entries = []
    for b in branches:
        try:
            entries.append(analyze_branch(b, args.remote, args.base))
        except RuntimeError as e:
            entries.append(
                {
                    "branch": b,
                    "ref": f"{args.remote}/{b}",
                    "kind": classify_kind(b),
                    "resolvable": False,
                    "ahead": None,
                    "behind": None,
                    "merged": False,
                    "files_changed": None,
                    "insertions": None,
                    "deletions": None,
                    "top_dirs": [],
                    "absorbed_files": 0,
                    "fully_absorbed": False,
                    "last_subject": "",
                    "last_author": "",
                    "last_date": "",
                    "head_sha": None,
                    "merge_base": None,
                    "note": f"error: {e}",
                }
            )

    entries.sort(key=sort_key)

    resolvable = sum(1 for e in entries if e.get("resolvable"))
    unresolvable = len(entries) - resolvable

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base": args.base,
        "remote": args.remote,
        "branch_count": len(entries),
        "resolvable_count": resolvable,
        "unresolvable_count": unresolvable,
        "branches": entries,
    }

    json_out = REPO_ROOT / args.json_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n")

    md_out = REPO_ROOT / args.md_out
    md_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.write_text(render_markdown(args.base, args.remote, entries))

    print(
        f"branch_matrix: {len(entries)} branches, {resolvable} resolvable, "
        f"{unresolvable} unresolvable-merge-base",
        file=sys.stderr,
    )
    print(f"  json: {json_out}", file=sys.stderr)
    print(f"  md:   {md_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
