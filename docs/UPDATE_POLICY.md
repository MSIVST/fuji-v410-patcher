# Update Policy

This project should stay boring on purpose. Each release should make a small number of well-understood changes, and future fixes should be easy to audit.

## Current Stable Patch Set

`v1.0.0` contains:

- Startup warning auto-advance.
- MP3 fresh-open `0 ms` seek-path patch.
- Map reminder interval changed from 28 days to 365 days.
- Map reminder UI text changed from `28 Days` to `1 Year`.

## Future Fix Path

Future work should be added as separate patch modules:

- `wma_*` for WMA decoder/playback stability work.
- `bt_*` for Bluetooth reconnect or notification behavior.
- `mp3_*` for additional MP3 playback behavior.
- `map_*` for map reminder or map UI behavior.
- `startup_*` for startup-flow behavior.

Each module should document:

- Patch name.
- Target firmware section.
- Logical firmware offset.
- Original expected bytes.
- Replacement bytes.
- User-visible behavior.
- Known risks.
- Test status.

## Versioning

- `v1.0.x`: bug fixes to the patcher tool or documentation only.
- `v1.x.0`: new optional patch modules, such as WMA or Bluetooth work.
- `v2.0.0`: incompatible behavior changes, new firmware families, or major CLI/GUI changes.
- `v1.1.0-beta.1`: prerelease builds for device testing before a stable release.

## Release Channels

- Stable releases should include only patches that have been tested on real hardware or are clearly documented as already verified.
- Experimental WMA/BT/media patches should ship as prereleases first.
- Diagnostic builds should be marked clearly and should not be recommended for normal users.

## Required Checks Before Release

- No Garmin/Suzuki firmware included.
- No patched `GUPDATE.GCD` included.
- No extracted `fw_all.bin`, `boot.bin`, map, voice, key, unlock, or resource files included.
- No personal paths, serial numbers, API keys, or private logs included.
- Known stock input hashes documented.
- Expected patched output hashes documented.
- Dry-run tested on at least one known stock input.
- Windows GUI launch tested.
- Recovery-to-stock instructions present.

## Suggested Future WMA/BT Workflow

1. Reproduce the issue on stock firmware or the latest stable patcher output.
2. Collect logs without personal device data where possible.
3. Identify a minimal firmware path and patch candidate.
4. Build a prerelease with the new fix disabled by default if practical.
5. Test on one unit first, with stock recovery media ready.
6. Ask for community test reports using the issue templates.
7. Promote to stable only after repeated successful reports.
