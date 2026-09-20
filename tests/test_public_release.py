from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

import fuji_v410_delta as delta
import fuji_v410_patcher as patcher


class PublicReleaseTests(unittest.TestCase):
    def test_release_identity_and_strict_cli(self) -> None:
        self.assertEqual(patcher.TOOL_VERSION, "1.2.1")
        self.assertEqual(
            patcher.default_output_path(Path("GUPDATE.GCD")).name,
            "GUPDATE_patched_v1.2.1.GCD",
        )
        help_text = patcher.build_arg_parser().format_help()
        self.assertIn("--overwrite", help_text)
        self.assertNotIn("allow-unknown", help_text)

    def test_embedded_delta_contract(self) -> None:
        spans = delta.load_delta()
        self.assertEqual(len(spans), delta.DELTA_SPAN_COUNT)
        self.assertEqual(sum(len(payload) for _, payload in spans), delta.DELTA_CHANGED_BYTES)
        self.assertEqual(delta.DELTA_SPAN_COUNT, 2092)
        self.assertEqual(delta.DELTA_CHANGED_BYTES, 87069)
        self.assertEqual(delta.STOCK_HOST_SHA256, patcher.SUPPORTED_HOST_SHA256)
        self.assertEqual(delta.PATCHED_HOST_SHA256, patcher.EXPECTED_PATCHED_HOST_SHA256)

        prior_end = -1
        for offset, payload in spans:
            self.assertGreater(offset, prior_end)
            self.assertTrue(payload)
            prior_end = offset + len(payload) - 1

        for _, feature_offset, _ in delta.FEATURES:
            self.assertTrue(
                any(start <= feature_offset < start + len(payload) for start, payload in spans),
                f"feature offset 0x{feature_offset:08X} is outside the embedded delta",
            )

    def test_atomic_write_is_no_clobber_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "result.bin"
            patcher.atomic_write_bytes(destination, b"first")
            with self.assertRaises(FileExistsError):
                patcher.atomic_write_bytes(destination, b"second")
            self.assertEqual(destination.read_bytes(), b"first")

            patcher.atomic_write_bytes(destination, b"second", overwrite=True)
            self.assertEqual(destination.read_bytes(), b"second")

    def test_distinct_path_guard_rejects_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            original = Path(directory) / "input.gcd"
            original.write_bytes(b"test")
            with self.assertRaises(ValueError):
                patcher.require_distinct_paths(
                    [("input", original), ("output", original.parent / "." / original.name)]
                )

            hardlink = Path(directory) / "hardlink.gcd"
            try:
                os.link(original, hardlink)
            except OSError:
                self.skipTest("hard links are unavailable")
            with self.assertRaises(ValueError):
                patcher.require_distinct_paths([("input", original), ("output", hardlink)])


if __name__ == "__main__":
    unittest.main()
