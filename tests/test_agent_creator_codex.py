"""Behavioral regression tests; no model, credentials, network, or external packages."""

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = Path(os.environ.get(
    "AGENT_CREATOR_VALIDATOR",
    ROOT / "skills/agent-creator-codex/scripts/validate-agent.py",
))
BASE = '''name = "case-analyst"
description = "Investigate a search case."
developer_instructions = "Inspect the supplied evidence and return findings with references."
'''


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def write(self, text=BASE, name="case-analyst.toml"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_validator(self, *args):
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), *map(str, args)],
            text=True, encoding="utf-8", capture_output=True, timeout=15,
        )
        self.assertNotIn("Traceback", result.stdout + result.stderr)
        return result

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def assert_error(self, result, text):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(text, result.stdout)

    def test_minimal_and_internal_model(self):
        for extra in ("", 'model = "maas-glm-5.2-volcengine-codeagent"\n',
                      'model_reasoning_effort = "provider-specific-effort"\n'):
            with self.subTest(extra=extra):
                self.assert_ok(self.run_validator(self.write(BASE + extra), "--strict"))

    def test_short_chinese_instructions_and_different_filename_are_valid(self):
        text = 'name = "analyst"\ndescription = "分析案例"\ndeveloper_instructions = "只读检查，返回证据。"\n'
        self.assert_ok(self.run_validator(self.write(text, "definition.toml"), "--strict"))

    def test_wrong_optional_types_and_enums(self):
        invalid = {
            "model": "123", "model_reasoning_effort": "[]",
            "model_reasoning_summary": '"impossible"',
            "model_verbosity": '"impossible"', "personality": '"unknown"',
            "features": '"disabled"', "skills": "false",
        }
        for key, value in invalid.items():
            with self.subTest(key=key):
                self.assert_error(self.run_validator(self.write(BASE + f"{key} = {value}\n"), "--strict"), key)

    def test_invalid_toml(self):
        self.assert_error(self.run_validator(self.write('[name = "case-analyst"]\n')), "TOML")

    def test_missing_and_blank_metadata(self):
        for text, key in ((BASE.replace('name = "case-analyst"\n', ""), "name"),
                          (BASE.replace('description = "Investigate a search case."', 'description = " "'), "description"),
                          (BASE.replace('developer_instructions = "Inspect the supplied evidence and return findings with references."', 'developer_instructions = " "'), "developer_instructions")):
            with self.subTest(key=key):
                self.assert_error(self.run_validator(self.write(text)), key)

    def test_nested_skills_rejects_bad_shapes(self):
        cases = [
            ('[skills]\ninclude_instructions = "false"\n', "include_instructions"),
            ('[skills]\nconfig = false\n', "config"),
            ('[skills]\nconfig = [1]\n', "config"),
            ('[skills]\nbundled = false\n', "bundled"),
            ('[skills.bundled]\nenabled = "false"\n', "enabled"),
            ('[[skills.config]]\nname = "x"\nenabled = "false"\n', "enabled"),
            ('[[skills.config]]\nenabled = false\n', "selector"),
            ('[[skills.config]]\nname = "x"\npath = "/tmp/x/SKILL.md"\nenabled = false\n', "selector"),
            ('[[skills.config]]\nname = " "\nenabled = false\n', "name"),
            ('[[skills.config]]\npath = 2\nenabled = false\n', "path"),
            ('[[skills.config]]\nname = "x"\n', "enabled"),
        ]
        for extra, key in cases:
            with self.subTest(extra=extra):
                self.assert_error(self.run_validator(self.write(BASE + extra), "--strict"), key)

    def test_supported_disables(self):
        extra = '''[features]
shell_tool = false
apps = false
plugins = false
memories = false
request_permissions_tool = false
[skills]
include_instructions = false
[skills.bundled]
enabled = false
[[skills.config]]
name = "example-skill"
enabled = false
[[skills.config]]
path = "C:/skills/other-skill/SKILL.md"
enabled = false
'''
        self.assert_ok(self.run_validator(self.write(BASE + extra), "--strict"))

    def test_feature_values_are_booleans(self):
        for value in ('"false"', "0", "[]"):
            with self.subTest(value=value):
                self.assert_error(self.run_validator(self.write(BASE + f"[features]\nshell_tool = {value}\n"), "--strict"), "shell_tool")

    def test_ineffective_settings_warn_and_strict_fails(self):
        for extra in ('sandbox_mode = "read-only"\n', '[features]\napps = true\n',
                      '[skills.bundled]\nenabled = true\n', '[tools]\nweb_search = false\n',
                      '[skills]\nmax_context_tokens = 1000\n'):
            with self.subTest(extra=extra):
                path = self.write(BASE + extra)
                ordinary = self.run_validator(path)
                self.assert_ok(ordinary)
                self.assertIn("WARNING", ordinary.stdout)
                self.assert_error(self.run_validator(path, "--strict"), "WARNING")

    def test_unknown_key_requires_target_version_verification(self):
        path = self.write(BASE + "future_extension = true\n")
        ordinary = self.run_validator(path)
        self.assert_ok(ordinary)
        self.assertIn("future_extension", ordinary.stdout)
        self.assertIn("not covered", ordinary.stdout)
        self.assert_error(self.run_validator(path, "--strict"), "future_extension")

    def test_capabilities_and_constraints_are_not_silently_accepted(self):
        for extra in ('[capabilities]\ncan_call_apis = true\n', '[constraints]\nmax_tool_calls = 50\n'):
            with self.subTest(extra=extra):
                self.assert_error(self.run_validator(self.write(BASE + extra), "--strict"), "WARNING")

    def test_bad_sandbox_container_does_not_crash(self):
        good = self.write(BASE, "good.toml")
        for value in ("[]", "{}", "1"):
            with self.subTest(value=value):
                bad = self.write(BASE.replace("case-analyst", "broken") + f"sandbox_mode = {value}\n", "broken.toml")
                result = self.run_validator(bad, good, "--strict")
                self.assert_error(result, "sandbox_mode")
                self.assertIn("2 file(s)", result.stdout)

    def test_bad_utf8_does_not_stop_batch(self):
        bad = self.root / "bad.toml"
        bad.write_bytes(b"\xff\xfe")
        result = self.run_validator(bad, self.write())
        self.assert_error(result, "UTF-8")
        self.assertIn("2 file(s)", result.stdout)

    def test_deeply_nested_toml_does_not_stop_batch(self):
        nested = "[" * 800 + "0" + "]" * 800
        bad = self.write(BASE.replace("case-analyst", "nested") +
                         f"[features]\nfuture_extension = {nested}\n", "nested.toml")
        result = self.run_validator(bad, self.write(), "--strict")
        self.assert_error(result, "nesting")
        self.assertIn("2 file(s)", result.stdout)

    def test_overlap_paths_are_deduplicated(self):
        path = self.write()
        result = self.run_validator(self.root, path, path, "--strict")
        self.assert_ok(result)
        self.assertIn("1 file(s)", result.stdout)

    def test_symlink_alias_is_not_a_second_role(self):
        path = self.write()
        alias = self.root / "alias.toml"
        try:
            alias.symlink_to(path)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable on this platform")
        result = self.run_validator(path, alias, "--strict")
        self.assert_ok(result)
        self.assertIn("1 file(s)", result.stdout)

    def test_duplicate_normalized_names(self):
        self.write(BASE.replace("case-analyst", "analyst"), "one.toml")
        self.write(BASE.replace("case-analyst", " analyst "), "two.toml")
        self.assert_error(self.run_validator(self.root), "duplicate name")

    def test_nickname_constraints(self):
        for value in ('[]', '[" "]', '["Atlas", " Atlas "]', '["测试"]', '[1]', '"Atlas"'):
            with self.subTest(value=value):
                self.assert_error(self.run_validator(self.write(BASE + f"nickname_candidates = {value}\n"), "--strict"), "nickname_candidates")
        self.assert_ok(self.run_validator(self.write(BASE + 'nickname_candidates = [" Atlas ", "Unit-2"]\n'), "--strict"))

    def test_role_layer_can_omit_standalone_metadata(self):
        path = self.write('model = "internal-model"\n', "layer.toml")
        self.assert_ok(self.run_validator(path, "--kind", "role-layer", "--strict"))
        self.assert_error(self.run_validator(path), "name")

    def test_role_layer_still_rejects_invalid_present_fields(self):
        path = self.write('developer_instructions = " "\n', "layer.toml")
        self.assert_error(self.run_validator(path, "--kind", "role-layer"), "developer_instructions")

    def test_empty_directory_is_reported_even_with_valid_input(self):
        empty = self.root / "empty"
        empty.mkdir()
        self.assert_error(self.run_validator(empty, self.write()), "no .toml files")

    def test_missing_path_is_reported(self):
        self.assert_error(self.run_validator(self.root / "missing.toml"), "does not exist")


class DocumentationTests(unittest.TestCase):
    def test_markdown_toml_examples_parse(self):
        skill = ROOT / "skills/agent-creator-codex"
        count = 0
        for path in skill.rglob("*.md"):
            for content in re.findall(r"```toml\s*\n(.*?)```", path.read_text(encoding="utf-8"), re.S):
                with self.subTest(path=path, content=content):
                    tomllib.loads(content)
                count += 1
        self.assertGreater(count, 0, "No TOML examples were checked")


if __name__ == "__main__":
    unittest.main()
