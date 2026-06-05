# Roadmap

This roadmap is intentionally cautious. Stable releases should prioritize tested, reversible, well-documented behavior.

## Stable: v1.0.0

- Startup warning auto-advance.
- MP3 end-of-track cutoff fix.
- 365-day map reminder interval.
- Public patcher distribution without firmware.

## Candidate: v1.1.0

- Improve region/test reporting.
- Add optional diagnostic report output improvements.
- Add clearer unsupported-firmware messages.

## Research: WMA

Goal: investigate WMA playback crashes without mixing the fix into stable builds prematurely.

Requirements before release:

- Reproducible WMA crash case.
- Logs or traces pointing to a specific failure path.
- Minimal patch candidate.
- Prerelease testing on real hardware.

## Research: Bluetooth

Goal: investigate Bluetooth reconnect notification behavior without affecting pairing, hands-free calling, or normal reconnect timing.

Requirements before release:

- Identify whether the message is UI-only, connection-state logic, or backend Bluetooth stack behavior.
- Avoid changing pairing, phonebook, call audio, or emergency behavior.
- Ship as prerelease until tested.

## Research: Media Database

Goal: understand stale media metadata and database rebuild behavior.

Possible outputs:

- Documentation-only guide.
- Safe user procedure for forcing rebuilds.
- Tooling that does not modify firmware.
