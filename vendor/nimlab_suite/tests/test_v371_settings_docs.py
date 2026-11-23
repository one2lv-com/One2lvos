"""v3.7.1: the README documents every setting Nim Lab reads."""

import os
import re
import unittest

from nimlab import config, settings_ref

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def reference():
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"<!-- settings-reference:start -->(.*?)<!-- settings-reference:end -->", text, re.S)
    return m.group(1) if m else ""


class TestSettingsDocs(unittest.TestCase):
    def test_every_setting_is_documented_with_a_description(self):
        ref = reference()
        self.assertTrue(ref, "README has no Settings reference section")
        missing, bare = [], []
        for path, _ in settings_ref.all_settings():
            m = re.search(r"^- `" + re.escape(path) + r"` \(default `[^\n]*?`\): (.+)$", ref, re.M)
            if not m:
                missing.append(path)
            elif len(m.group(1).strip()) < 12:
                bare.append(path)
        self.assertEqual(missing, [], "settings missing from the README's Settings reference")
        self.assertEqual(bare, [], "settings without a real description")

    def test_no_stale_entries(self):
        known = {p for p, _ in settings_ref.all_settings()}
        listed = re.findall(r"^- `([a-z_.]+)` \(default", reference(), re.M)
        self.assertTrue(listed)
        self.assertEqual(sorted(set(listed) - known), [], "README lists settings that no longer exist")

    def test_shipped_config_has_every_cluster_section(self):
        cfg = config.load_json(os.path.join(ROOT, "config_cluster.json"), {})
        for section in config.DEFAULT_CLUSTER:
            if section == "roles":
                continue
            self.assertIn(section, cfg, f"config_cluster.json has no {section}")

    def test_new_371_settings_are_listed(self):
        ref = reference()
        for p in ("voice_settings.fast_route", "voice_settings.turn_timeout_sec", "memory_settings.long_term.ords.auth",
                  "server.self_test_timeout_sec", "server.bugs.keep_days", "mcp_settings.dedicated_endpoint",
                  "routing_settings.environment_block"):
            self.assertIn("`" + p + "`", ref)


if __name__ == "__main__":
    unittest.main()
