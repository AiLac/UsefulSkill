#!/usr/bin/env python3
"""Statically lint Codex agent TOML files (Python 3.11+, standard library only).

Usage: validate-agent.py <file-or-directory> [...] [--strict]
                         [--kind standalone|role-layer]

Checks a bounded set of fields against openai/codex rust-v0.167.2. Unknown
fields warn; this is not a complete ConfigToml schema or a runtime/model check.
Exit 1 for errors, or for warnings with --strict; argparse usage errors exit 2.
Derived from CowboyLogic/ai-dev; see ../LICENSE and ../NOTICE.md.
"""

from __future__ import annotations

import argparse
import difflib
import os
from pathlib import Path
import re
import sys

try:
    import tomllib
except ImportError:  # pragma: no cover
    sys.exit("Python 3.11+ is required (tomllib)")


REQUIRED = ("name", "description", "developer_instructions")
TEXT_FIELDS = (*REQUIRED, "model", "model_reasoning_effort")
ENUM_FIELDS = {
    "model_reasoning_summary": {"auto", "concise", "detailed", "none"},
    "model_verbosity": {"low", "medium", "high"},
    "personality": {"none", "friendly", "pragmatic"},
}
DISABLE_ONLY_FEATURES = {
    "shell_tool", "apps", "plugins", "memories", "memory_tool",
    "request_permissions_tool",
}
# Parse shape only: these settings do not override the parent's authority.
IGNORED_FIELDS = {
    "sandbox_mode": ((str,), "the child inherits the parent's sandbox"),
    "approval_policy": ((str, dict), "the child inherits the parent's approval policy"),
    "mcp_servers": ((dict,), "configure MCP servers on the parent session"),
    "model_provider": ((str,), "configure the provider on the parent session"),
    "web_search": ((str,), "configure web search on the parent session"),
    "service_tier": ((str,), "the child inherits the root session's service tier"),
    "shell_environment_policy": ((dict,), "configure this on the parent session"),
    "sandbox_workspace_write": ((dict,), "configure this on the parent session"),
    "tools": ((dict,), "this is not a role tool allowlist; parent MCP tools remain inherited"),
}
KNOWN_KEYS = set(TEXT_FIELDS) | set(ENUM_FIELDS) | set(IGNORED_FIELDS) | {
    "nickname_candidates", "features", "skills",
}
FIELD_HINTS = {
    "capabilities": "there is no generic role capability table in the checked baseline",
    "constraints": "put workflow limits in developer_instructions; prose is not enforced quota",
    "system_prompt": "use developer_instructions for role instructions",
    "maxTurns": "this is a Claude Code field, not a Codex role field",
    "permissionMode": "configure permissions on the parent session",
    "disallowedTools": "Codex does not use a role tool denylist with this field",
}


class Result:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0

    def error(self, path: Path, message: str) -> None:
        self.errors += 1
        print(f"ERROR   {path}: {message}")

    def warn(self, path: Path, message: str) -> None:
        self.warnings += 1
        print(f"WARNING {path}: {message}")


def unknown_key(res: Result, path: Path, key: str, known: set[str]) -> None:
    matches = difflib.get_close_matches(key, sorted(known), n=1, cutoff=0.75)
    hint = FIELD_HINTS.get(key)
    suffix = f"; {hint}" if hint else ""
    if matches:
        suffix += f"; did you mean `{matches[0]}`?"
    res.warn(path, f"`{key}` is not covered by this validator; verify the target Codex version{suffix}")


def check_string(res: Result, path: Path, key: str, value: object, *, allow_blank: bool = False) -> None:
    if not isinstance(value, str):
        res.error(path, f"`{key}` must be a string")
    elif not allow_blank and not value.strip():
        res.error(path, f"`{key}` must not be blank")


def check_enum(res: Result, path: Path, key: str, value: object, choices: set[str]) -> None:
    # Check the type before set membership: TOML arrays and tables are unhashable.
    if not isinstance(value, str) or value not in choices:
        res.error(path, f"`{key}` must be one of {', '.join(sorted(choices))}")


def check_disable(res: Result, path: Path, key: str, value: object) -> None:
    if not isinstance(value, bool):
        res.error(path, f"`{key}` must be a boolean")
    elif value:
        res.warn(path, f"`{key} = true` has no effect in a role file; only disabling is applied")


def check_features(res: Result, path: Path, value: object) -> None:
    if not isinstance(value, dict):
        res.error(path, "`features` must be a TOML table")
        return
    for key, enabled in value.items():
        if key in DISABLE_ONLY_FEATURES:
            check_disable(res, path, f"features.{key}", enabled)
        else:
            # Other features can have structured values. Do not invent a bool-only schema.
            res.warn(path, f"`features.{key}` is not covered as a role override; "
                          "verify the target version (not applied in the checked baseline)")


def check_skills(res: Result, path: Path, value: object) -> None:
    if not isinstance(value, dict):
        res.error(path, "`skills` must be a TOML table")
        return
    known = {"config", "bundled", "include_instructions", "max_context_tokens"}
    for key in value.keys() - known:
        unknown_key(res, path, f"skills.{key}", {f"skills.{k}" for k in known})
    if "include_instructions" in value:
        check_disable(res, path, "skills.include_instructions", value["include_instructions"])
    if "max_context_tokens" in value:
        tokens = value["max_context_tokens"]
        if type(tokens) is not int or tokens < 1:
            res.error(path, "`skills.max_context_tokens` must be a positive integer")
        else:
            res.warn(path, "`skills.max_context_tokens` is ignored in a role file; "
                           "it is not a subagent context-window quota")
    if "bundled" in value:
        bundled = value["bundled"]
        if not isinstance(bundled, dict):
            res.error(path, "`skills.bundled` must be a TOML table")
        else:
            for key in bundled.keys() - {"enabled"}:
                unknown_key(res, path, f"skills.bundled.{key}", {"skills.bundled.enabled"})
            if "enabled" in bundled:
                check_disable(res, path, "skills.bundled.enabled", bundled["enabled"])
            else:
                res.warn(path, "`skills.bundled` without `enabled = false` has no role override effect")
    if "config" not in value:
        return
    entries = value["config"]
    if not isinstance(entries, list):
        res.error(path, "`skills.config` must be an array of TOML tables")
        return
    for index, entry in enumerate(entries):
        key = f"skills.config[{index}]"
        if not isinstance(entry, dict):
            res.error(path, f"`{key}` must be a TOML table")
            continue
        for field in entry.keys() - {"name", "path", "enabled"}:
            unknown_key(res, path, f"{key}.{field}", {f"{key}.{k}" for k in ("name", "path", "enabled")})
        if "enabled" not in entry:
            res.error(path, f"`{key}.enabled` is required")
        else:
            check_disable(res, path, f"{key}.enabled", entry["enabled"])
        selectors = [field for field in ("name", "path") if field in entry]
        if len(selectors) != 1:
            res.error(path, f"`{key}` needs exactly one selector: `name` or `path`; "
                            "Codex ignores entries with neither or both (lint policy error)")
        for field in selectors:
            check_string(res, path, f"{key}.{field}", entry[field])


def check_nicknames(res: Result, path: Path, value: object) -> None:
    if not isinstance(value, list) or not value:
        res.error(path, "`nickname_candidates` must be a non-empty array of strings")
        return
    seen: set[str] = set()
    for nickname in value:
        if not isinstance(nickname, str) or not nickname.strip():
            res.error(path, "`nickname_candidates` must contain non-blank strings")
            continue
        nickname = nickname.strip()
        if nickname in seen:
            res.error(path, f"`nickname_candidates` contains duplicate `{nickname}` after trimming")
        seen.add(nickname)
        if not re.fullmatch(r"[A-Za-z0-9 _-]+", nickname):
            res.error(path, "`nickname_candidates` may contain only ASCII letters, digits, spaces, - and _")


def validate_file(path: Path, names: dict[str, Path], res: Result, kind: str = "standalone") -> None:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except UnicodeError as exc:
        res.error(path, f"file is not valid UTF-8: {exc}")
        return
    except tomllib.TOMLDecodeError as exc:
        res.error(path, f"TOML does not parse: {exc}")
        return
    except RecursionError:
        res.error(path, "TOML nesting exceeds this parser's recursion limit")
        return
    except OSError as exc:
        res.error(path, f"cannot read: {exc}")
        return

    if kind == "standalone":
        for key in REQUIRED:
            if key not in data:
                res.error(path, f"missing required `{key}`")
    for key in TEXT_FIELDS:
        if key in data:
            check_string(res, path, key, data[key], allow_blank=(kind == "role-layer" and key == "name"))
    for key, choices in ENUM_FIELDS.items():
        if key in data:
            check_enum(res, path, key, data[key], choices)

    # Role identity may depend on an external declaration; this mode does not check registration.
    name = data.get("name")
    if kind == "standalone" and isinstance(name, str) and name.strip():
        name = name.strip()
        if name in names:
            res.error(path, f"duplicate name `{name}` (also in {names[name]})")
        else:
            names[name] = path

    for key, value in data.items():
        if key in IGNORED_FIELDS:
            types, note = IGNORED_FIELDS[key]
            if not isinstance(value, types):
                expected = " or ".join("table" if t is dict else "string" for t in types)
                res.error(path, f"`{key}` must be a {expected}")
            else:
                res.warn(path, f"`{key}` is ignored as a role override: {note}; "
                               "nested parent settings are not validated here")
        elif key not in KNOWN_KEYS:
            unknown_key(res, path, key, KNOWN_KEYS)
    if "sandbox_mode" in data and isinstance(data["sandbox_mode"], str):
        check_enum(res, path, "sandbox_mode", data["sandbox_mode"],
                   {"read-only", "workspace-write", "danger-full-access"})
    if "features" in data:
        check_features(res, path, data["features"])
    if "skills" in data:
        check_skills(res, path, data["skills"])
    if "nickname_candidates" in data:
        check_nicknames(res, path, data["nickname_candidates"])


def collect(paths: list[Path], res: Result) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for target in paths:
        try:
            if not target.exists():
                res.error(target, "path does not exist")
                continue
            candidates = sorted(target.rglob("*.toml")) if target.is_dir() else [target]
            if not candidates:
                res.error(target, "no .toml files found")
            for candidate in candidates:
                if not candidate.is_file():
                    res.error(candidate, "not a regular file")
                    continue
                canonical = candidate.resolve()
                identity = os.path.normcase(str(canonical))
                if identity not in seen:
                    seen.add(identity)
                    files.append(canonical)
        except (OSError, RuntimeError) as exc:
            res.error(target, f"cannot scan path: {exc}")
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", type=Path, help="files or directories to scan recursively")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--kind", choices=("standalone", "role-layer"), default="standalone",
                        help="role-layer permits metadata supplied by an external declaration")
    args = parser.parse_args()
    res = Result()
    files = collect(args.paths, res)
    names: dict[str, Path] = {}
    for path in files:
        validate_file(path, names, res, args.kind)
    print(f"\n{len(files)} file(s), {res.errors} error(s), {res.warnings} warning(s)")
    print("Static checks only; target Codex loading, model availability and runtime behavior remain unverified.")
    return 1 if res.errors or (args.strict and res.warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
