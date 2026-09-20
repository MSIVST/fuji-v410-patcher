# Changelog

## v1.2.0 - 2026-09-19

Release of the complete, non-selectable 2026.09.16 patch set.

- Adds Ogg/Vorbis playback and rejects streams with more than two channels.
- Rejects WMA Pro, WMA Voice, and unsupported WMA Lossless profiles before indexing.
- Adds WMA cover art, progressive JPEG dimensions, and JPEG artwork in supported ID3v2.3/v2.4 APIC frames.
- Documents that corrupt or unreadable JPEG artwork is omitted and PNG artwork is not supported by the unit.
- Pins all five supported regional stock-container hashes and the shared host-payload hashes.
- Adds strict path-alias rejection, no-clobber output defaults, atomic output/report publication, and read-back verification.
- Retains the v1.0.0 startup, MP3 seek, and map-reminder changes.
- Does not include Garmin/Suzuki firmware or patched firmware.

The North American build has physical-unit evidence. AU/EU/IN/RU support is
offline-verified but has not been tested on corresponding regional hardware.

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
