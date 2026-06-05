# Changelog

## v1.0.0 - 2026-06-05

Initial public patcher release.

- Adds startup-warning auto-advance patch.
- Adds MP3 fresh-open `0 ms` seek-path patch for the observed end-of-track cutoff.
- Changes map update reminder interval from 28 days to 365 days.
- Changes visible reminder text from `28 Days` to `1 Year`.
- Includes 32-bit Windows GUI EXE release asset and source Python scripts.
- Does not include Garmin/Suzuki firmware or patched firmware.

## Future Versioning

- Patch-only fixes: increment `v1.0.x`.
- New optional patch modules, such as WMA or Bluetooth behavior changes: increment `v1.x.0`.
- Major behavior changes, new target firmware families, or incompatible CLI changes: increment `v2.0.0`.
- Untested device experiments should use prerelease tags such as `v1.1.0-beta.1`.
