#!/usr/bin/env python3
from __future__ import annotations

import re

PRESETS = ("laravel", "next", "legacy")
RESERVED_TAG = "template"
VALID_TAGS = frozenset(PRESETS) | {RESERVED_TAG}

BLOCK_OPEN_PATTERNS = (
    re.compile(r"^\s*#\s*>>>\s*preset:([a-z,]+)\s*$"),
    re.compile(r"^\s*<!--\s*>>>\s*preset:([a-z,]+)\s*-->\s*$"),
)
BLOCK_CLOSE_PATTERNS = (
    re.compile(r"^\s*#\s*<<<\s*preset\s*$"),
    re.compile(r"^\s*<!--\s*<<<\s*preset\s*-->\s*$"),
)
LINE_SUFFIX_PATTERNS = (
    re.compile(r"[ \t]*#[ \t]*preset:([a-z,]+)[ \t]*$"),
    re.compile(r"[ \t]*<!--[ \t]*preset:([a-z,]+)[ \t]*-->[ \t]*$"),
)


class MarkupError(ValueError):
    pass


def match_any(patterns, line):
    for pattern in patterns:
        match = pattern.match(line) if pattern.pattern.startswith("^") else pattern.search(line)
        if match:
            return match
    return None


def parse_tags(raw: str, path: str, line_no: int) -> frozenset[str]:
    tags = frozenset(part for part in raw.split(",") if part)
    if not tags or tags - VALID_TAGS:
        raise MarkupError(f"{path}:{line_no}: invalid preset tags {raw!r}")
    return tags


def prune_text(text: str, preset: str, path: str) -> str:
    out: list[str] = []
    block_tags: frozenset[str] | None = None
    block_line = 0
    for line_no, line in enumerate(text.splitlines(keepends=True), start=1):
        stripped = line.rstrip("\n")
        open_match = match_any(BLOCK_OPEN_PATTERNS, stripped)
        close_match = match_any(BLOCK_CLOSE_PATTERNS, stripped)
        if open_match:
            if block_tags is not None:
                raise MarkupError(f"{path}:{line_no}: nested preset block")
            block_tags = parse_tags(open_match.group(1), path, line_no)
            block_line = line_no
            continue
        if close_match:
            if block_tags is None:
                raise MarkupError(f"{path}:{line_no}: close marker without open block")
            block_tags = None
            continue
        if block_tags is not None:
            if preset in block_tags:
                out.append(line)
            continue
        suffix = match_any(LINE_SUFFIX_PATTERNS, stripped)
        if suffix:
            tags = parse_tags(suffix.group(1), path, line_no)
            if preset in tags:
                newline = "\n" if line.endswith("\n") else ""
                out.append(stripped[: suffix.start()].rstrip() + newline)
            continue
        out.append(line)
    if block_tags is not None:
        raise MarkupError(f"{path}:{block_line}: unclosed preset block")
    return "".join(out)
