#!/usr/bin/env python3
"""
ACDP cross-artifact consistency checker.

A spec change is usually a multi-file change (fixture + profiles.json +
profiles.md + conformance README). This gate enforces the wiring that the
individual validators cannot see:

  1. Every conformance fixture's `id` equals its filename stem, and ids are unique.
  2. Every fixture belongs to a family declared in registries/profiles.json
     `fixture_families` (longest-prefix match) — a typo'd prefix would otherwise
     be silently skipped by the conformance runner.
  3. Every fixture file is referenced by at least one profile in profiles.json,
     and every fixture referenced in profiles.json exists on disk.
  4. Every fixture's short id (e.g. `pub-011`) is covered in registries/profiles.md,
     either literally or inside a `fam-001`..`fam-014` range; every short id
     mentioned in profiles.md resolves to exactly one fixture file.
  5. Every fixture filename appears in the schemas/conformance/README.md index.
  6. Every error code asserted by a fixture exists in registries/error-codes.md.
  7. Every examples/ subdirectory is routed (validated or syntax-checked) in
     scripts/validate-json.sh — a new directory must be consciously wired in.
  8. Every schema under schemas/json/ has a unique $id.
  9. Every repo-relative markdown link resolves to an existing file, and every
     fragment (`#anchor`) resolves to a real heading in the target file (GitHub
     slug rules) — every promotion renames a §2.x heading, and a renamed heading
     silently breaks every inbound anchor.
 10. Per-profile fixture placement: every fixture a profile lists in
     profiles.json is covered in that profile's own section of profiles.md
     (literal mention, `fam-001..N` range, or `fam-*` wildcard) — checks 3/4
     only prove a fixture is referenced *somewhere*, so a fixture moved to the
     wrong profile in one file would otherwise pass.

Exits 0 if all checks pass, 1 otherwise.
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
CONFORMANCE = ROOT / "schemas" / "conformance"
SCHEMAS = ROOT / "schemas" / "json"
EXAMPLES = ROOT / "examples"
REGISTRIES = ROOT / "registries"

errors = []


def err(check, msg):
    errors.append(f"[{check}] {msg}")


SHORT_ID_RE = re.compile(r"\b([a-z][a-z-]*-\d{3})\b")
SHORT_ID_EXACT = re.compile(r"[a-z][a-z-]*-\d{3}")
# Range notations used in profiles.md: `fam-001`..`fam-012` and `fam-001..005`
RANGE_RE = re.compile(r"([a-z][a-z-]*-)(\d{3})`?\s*\.\.\s*`?(?:[a-z][a-z-]*-)?(\d{3})")


def short_of(token):
    """'pub-002-hash-mismatch' -> 'pub-002'; returns None if no short id prefix."""
    m = SHORT_ID_RE.match(token)
    return m.group(1) if m else None


def load_fixtures():
    """Return {short_id: path}. Fixture files carry the short id (e.g. 'can-001')
    in their `id` field; the filename stem is `<id>-<slug>`."""
    fixtures = {}
    for path in sorted(CONFORMANCE.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            err("fixture-json", f"{path.name}: {e}")
            continue
        fid = data.get("id")
        if not fid or not SHORT_ID_EXACT.fullmatch(fid):
            err("fixture-id", f"{path.name}: id {fid!r} is not of the form <family>-<NNN>")
            continue
        if not (path.stem == fid or path.stem.startswith(fid + "-")):
            err("fixture-id", f"{path.name}: filename does not start with its id {fid!r}")
        if fid in fixtures:
            err("fixture-id", f"duplicate fixture id {fid!r} ({path.name} and {fixtures[fid].name})")
        fixtures[fid] = path
    return fixtures


def check_families(fixtures, families):
    # Longest-prefix match so data-ref-ssrf-001 resolves to data-ref-ssrf, not data-ref.
    ordered = sorted(families, key=len, reverse=True)
    for fid in fixtures:
        if not any(fid.startswith(fam + "-") for fam in ordered):
            err("fixture-family",
                f"{fid}: no matching family in registries/profiles.json fixture_families "
                f"(known: {', '.join(sorted(families))})")


def check_profiles_json(fixtures, profiles_json):
    stems = {p.stem for p in fixtures.values()}

    # Short ids referenced anywhere in profiles.json (lists and prose alike).
    refs = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for i in o:
                walk(i)
        elif isinstance(o, str):
            refs.update(SHORT_ID_RE.findall(o))

    walk(profiles_json.get("profiles", []))

    # Fixture ids explicitly listed in the manifest lists (not prose fields)
    # MUST resolve to a real fixture file.
    listed = set()
    for p in profiles_json.get("profiles", []):
        for key in ("required_fixtures", "required_fixtures_added", "tolerated_outcomes"):
            listed.update(p.get(key, []) or [])
        for cond in p.get("conditional_fixtures", []) or []:
            listed.update(cond.get("fixtures", []) or [])

    # 3a. every listed reference resolves to a real fixture (full stem or short id)
    for ref in sorted(listed):
        if ref not in stems and short_of(ref) not in fixtures:
            err("profiles-json", f"listed fixture {ref!r} does not exist under schemas/conformance/")

    # 3b. every fixture is referenced somewhere in profiles.json
    for fid, path in sorted(fixtures.items()):
        if fid not in refs:
            err("profiles-json", f"fixture {path.stem} is not referenced by any profile in registries/profiles.json")


def expand_ranges(text):
    """Expand `fam-001`..`fam-012` and `fam-001..005` notations into short ids."""
    ids = set()
    for fam, start, end in RANGE_RE.findall(text):
        for n in range(int(start), int(end) + 1):
            ids.add(f"{fam}{n:03d}")
    return ids


def check_profiles_md(fixtures):
    text = (REGISTRIES / "profiles.md").read_text()
    covered = set(SHORT_ID_RE.findall(text)) | expand_ranges(text)

    # 4a. every fixture is covered in profiles.md
    for fid, path in sorted(fixtures.items()):
        if fid not in covered:
            err("profiles-md", f"fixture {path.stem} ({fid}) is not mentioned in registries/profiles.md")

    # 4b. every short id mentioned in profiles.md resolves to a fixture.
    # Restrict to ids whose family exists as a fixture family, so prose like
    # RFC section references never false-positive.
    families = {fid.rsplit("-", 1)[0] for fid in fixtures}
    for short in sorted(covered):
        fam = short.rsplit("-", 1)[0]
        if fam in families and short not in fixtures:
            err("profiles-md", f"registries/profiles.md mentions {short!r} but no such fixture exists")


def check_conformance_readme(fixtures):
    text = (CONFORMANCE / "README.md").read_text()
    covered = set(SHORT_ID_RE.findall(text)) | expand_ranges(text)
    for fid, path in sorted(fixtures.items()):
        if fid not in covered:
            err("conformance-readme", f"fixture {path.stem} missing from schemas/conformance/README.md index")


def registered_error_codes():
    text = (REGISTRIES / "error-codes.md").read_text()
    return set(re.findall(r"^\|\s*`([a-z_]+)`", text, flags=re.MULTILINE))


def check_error_codes(fixtures):
    codes = registered_error_codes()
    if not codes:
        err("error-codes", "could not parse any error codes from registries/error-codes.md")
        return
    for fid, path in sorted(fixtures.items()):
        data = json.loads(path.read_text())
        used = set()

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("error_code", "code") and isinstance(v, str) and re.fullmatch(r"[a-z_]+", v):
                        used.add(v)
                    walk(v)
            elif isinstance(o, list):
                for i in o:
                    walk(i)

        walk(data)
        for c in sorted(used - codes):
            err("error-codes", f"{fid}: error code {c!r} is not in registries/error-codes.md")


def check_examples_routed():
    script = (ROOT / "scripts" / "validate-json.sh").read_text()
    for d in sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir()):
        if f"${{EXAMPLES_DIR}}/{d}" not in script:
            err("examples-routing",
                f"examples/{d}/ is not routed in scripts/validate-json.sh "
                f"(add a validate_dir_against or syntax_check_dir line, or it will never be validated)")


# ── Check 9: markdown links and anchors ──────────────────────────────────────

FENCE_RE = re.compile(r"^(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
# Inline links/images: [text](target) / ![alt](target "title"); target may be
# wrapped in <angle brackets>. Deliberately does not match targets containing
# parentheses or whitespace — repo-relative paths never carry either.
LINK_RE = re.compile(r"!?\[[^\]^\[]*\]\(<?([^()<>\s]+)>?(?:\s+\"[^\"]*\")?\)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def strip_fences(text):
    """Return the markdown text with fenced code blocks blanked out (line count
    preserved so reported line numbers stay real)."""
    out, in_fence, fence_mark = [], False, None
    for line in text.splitlines():
        m = FENCE_RE.match(line.strip())
        if m and not in_fence:
            in_fence, fence_mark = True, m.group(1)
            out.append("")
        elif in_fence and line.strip().startswith(fence_mark):
            in_fence = False
            out.append("")
        else:
            out.append("" if in_fence else line)
    return "\n".join(out)


def github_slug(heading):
    """GitHub's heading→anchor slug: strip markdown/link syntax, lowercase,
    drop everything but word chars, spaces, and hyphens, spaces→hyphens."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # links → text
    text = re.sub(r"[`*_~]", "", text)                          # emphasis/code
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def markdown_anchors(path, _cache={}):
    """Set of valid GitHub anchors for a markdown file (duplicate headings get
    -1, -2, … suffixes, as on GitHub)."""
    if path not in _cache:
        anchors, counts = set(), {}
        for line in strip_fences(path.read_text()).splitlines():
            m = HEADING_RE.match(line)
            if not m:
                continue
            slug = github_slug(m.group(2))
            n = counts.get(slug, 0)
            counts[slug] = n + 1
            anchors.add(slug if n == 0 else f"{slug}-{n}")
        _cache[path] = anchors
    return _cache[path]


def tracked_markdown_files():
    try:
        names = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "*.md"],
            capture_output=True, text=True, check=True,
        ).stdout.split("\n")
        return [ROOT / n for n in names if n]
    except (OSError, subprocess.CalledProcessError):
        # Not a git checkout (e.g. an exported tarball): fall back to a walk,
        # skipping the locally-ignored directories.
        skip = {".git", "node_modules", "temp", "plans"}
        return [p for p in ROOT.rglob("*.md")
                if not (set(p.relative_to(ROOT).parts[:-1]) & skip)]


def check_markdown_links():
    for path in sorted(tracked_markdown_files()):
        rel = path.relative_to(ROOT)
        text = strip_fences(path.read_text())
        for lineno, line in enumerate(text.splitlines(), 1):
            line = INLINE_CODE_RE.sub("", line)
            for target in LINK_RE.findall(line):
                target = unquote(target)
                if SCHEME_RE.match(target) or target.startswith("//"):
                    continue  # external URL / explicit scheme (https:, did:, acdp:, mailto:)
                if target.startswith("#"):
                    dest, frag = path, target[1:]
                else:
                    part, _, frag = target.partition("#")
                    dest = (ROOT / part.lstrip("/")) if part.startswith("/") \
                        else (path.parent / part)
                    try:
                        dest = dest.resolve()
                        dest.relative_to(ROOT)
                    except (OSError, ValueError):
                        err("md-link", f"{rel}:{lineno}: link target {target!r} escapes the repository")
                        continue
                    if not dest.exists():
                        err("md-link", f"{rel}:{lineno}: broken link — {target!r} does not exist")
                        continue
                if frag and dest.suffix == ".md" and dest.is_file():
                    if frag.lower() not in markdown_anchors(dest):
                        err("md-anchor",
                            f"{rel}:{lineno}: broken anchor — "
                            f"{'#' + frag if dest == path else target!r} does not match any heading in "
                            f"{dest.relative_to(ROOT)}")


# ── Check 10: per-profile fixture placement (profiles.json ↔ profiles.md) ────

WILDCARD_RE = re.compile(r"([a-z][a-z-]*)-\*")


def profile_fixture_sets(profiles_json):
    """{profile_id: set of short fixture ids that profile lists in the
    machine-readable manifest} — manifest lists only, never prose fields."""
    sets = {}
    for p in profiles_json.get("profiles", []):
        listed = []
        for key in ("required_fixtures", "required_fixtures_added",
                    "tolerated_outcomes", "self_test_only", "self_test_only_added"):
            listed.extend(p.get(key, []) or [])
        for cond in p.get("conditional_fixtures", []) or []:
            listed.extend(cond.get("fixtures", []) or [])
        # Entries are fixture stems (or short ids), possibly with a prose tail
        # (self_test_only) — take the leading short id only; a pure-prose entry
        # contributes nothing.
        sets[p["id"]] = {sid for sid in (short_of(e) for e in listed) if sid}
    return sets


def profiles_md_sections():
    """{profile_id: section text} — each `### \\`id\\`` block in profiles.md up
    to the next heading of the same-or-higher level."""
    text = (REGISTRIES / "profiles.md").read_text()
    sections = {}
    matches = list(re.finditer(r"^###\s+`([^`]+)`.*$", text, flags=re.MULTILINE))
    for i, m in enumerate(matches):
        end = len(text)
        nxt = re.search(r"^#{1,3}\s", text[m.end():], flags=re.MULTILINE)
        if nxt:
            end = m.end() + nxt.start()
        sections[m.group(1)] = text[m.start():end]
    return sections


def check_profile_placement(fixtures, profiles_json):
    sections = profiles_md_sections()
    families = {fid.rsplit("-", 1)[0] for fid in fixtures}
    for pid, json_ids in profile_fixture_sets(profiles_json).items():
        section = sections.get(pid)
        if section is None:
            err("profile-placement",
                f"profile {pid!r} (profiles.json) has no `### \\`{pid}\\`` section in registries/profiles.md")
            continue
        covered = set(SHORT_ID_RE.findall(section)) | expand_ranges(section)
        for fam in WILDCARD_RE.findall(section):
            if fam in families:
                covered.update(fid for fid in fixtures if fid.rsplit("-", 1)[0] == fam)
        for fid in sorted(json_ids - covered):
            err("profile-placement",
                f"profile {pid!r}: fixture {fid} is listed in profiles.json but not covered in "
                f"that profile's section of registries/profiles.md — wrong-profile placement or a missed mirror edit")


def check_schema_ids():
    seen = {}
    for path in sorted(SCHEMAS.glob("*.schema.json")):
        try:
            sid = json.loads(path.read_text()).get("$id")
        except json.JSONDecodeError as e:
            err("schema-id", f"{path.name}: {e}")
            continue
        if not sid:
            err("schema-id", f"{path.name}: missing $id")
        elif sid in seen:
            err("schema-id", f"duplicate $id {sid!r} ({path.name} and {seen[sid]})")
        else:
            seen[sid] = path.name


def main():
    profiles_json = json.loads((REGISTRIES / "profiles.json").read_text())
    families = set(profiles_json.get("fixture_families", {}))
    if not families:
        err("profiles-json", "registries/profiles.json has no fixture_families map")

    fixtures = load_fixtures()
    if not fixtures:
        err("fixtures", "no fixtures found under schemas/conformance/")

    check_families(fixtures, families)
    check_profiles_json(fixtures, profiles_json)
    check_profiles_md(fixtures)
    check_conformance_readme(fixtures)
    check_error_codes(fixtures)
    check_examples_routed()
    check_schema_ids()
    check_markdown_links()
    check_profile_placement(fixtures, profiles_json)

    if errors:
        print(f"✗ {len(errors)} consistency error(s):", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)
    print(f"✓ Cross-artifact consistency: {len(fixtures)} fixtures wired into "
          f"profiles.json, profiles.md, and the conformance README; error codes, "
          f"example routing, schema $ids, per-profile fixture placement, and "
          f"markdown links/anchors consistent.")


if __name__ == "__main__":
    main()
