# Fuji v4.10 Patcher Technicals

This document describes the `v1.2.1` patch set, validation model, supported
inputs, build, and verification boundaries. The patcher contains transformation
data and code only; it does not contain Garmin/Suzuki firmware.

## Compatibility Boundary

- Target: Suzuki Garmin Fuji firmware v4.10.
- Accepted regions: NA, AU, EU, IN, and RU.
- Hardware ID: `0x05BC`.
- Software version: `0x019A` (v4.10).
- Patched host-region type: `0x02BD`.
- Physically tested unit family: North American `39920-61M80`.
- `39920-61MR1` / `39920-61MR2` / `39920-61MR3`: unverified.
- AU/EU/IN/RU: transformation verified offline; corresponding regional
  hardware has not been tested.

All five supported regional containers carry a byte-identical `0x02BD` host
payload. Their maps and other surrounding resources differ, so the patcher
preserves the input container and changes only the shared host payload plus the
GCD checksum bytes that cover it.

## How the Patcher Works

1. It reads the complete supplied `GUPDATE.GCD` and calculates its SHA-256.
2. The complete-file hash must match one of the five pinned stock files. There
   is no unknown-file override.
3. It parses the GCD structure and locates the v4.10 `0x02BD` host region.
4. It verifies the host hardware/software identity and exact stock host hash.
5. It decodes the embedded verified delta and applies its sorted, non-overlapping
   spans to the host payload.
6. It verifies the exact patched host SHA-256.
7. It repairs the affected visible GCD checksum blocks.
8. It verifies the expected complete patched-container SHA-256 for the detected
   region.
9. Unless `--dry-run` was selected, it atomically publishes the output file and
   reads it back to verify length and SHA-256.

The embedded delta contains `2,092` spans and changes `87,069` host-payload
bytes. Features are installed together because codec hooks, helpers, and code
caves have dependencies; individual feature selection is not supported.

### Shared Host Hashes

| State | SHA-256 |
|---|---|
| Official stock host | `F566A42E1EA7A2CACD243E884A721209C024FB370635194F3C27B8B66928D3B6` |
| Patched host | `F550DBF7D3B9BC103297BBC315369D53C6C2738FE9ED83ABCB860FA3D59CC9F6` |

## Patch Set

| Patch | Behavior |
|---|---|
| `ogg_support` | Adds Ogg/Vorbis codec dispatch and decoder support. |
| `ogg_playback_fixes` | Repairs Ogg open, seek, fast-open, no-metadata, and oversized-artwork playback paths. |
| `ogg_channel_guard` | Rejects Vorbis streams with more than two channels instead of allowing the observed freeze/reboot path. |
| `unsupported_media_admission` | Rejects unsupported media before indexing: Vorbis above two channels, WMA Pro, WMA Voice, and WMA Lossless above two channels or 16-bit samples. |
| `wma_artwork_fix` | Corrects the WMA artwork file-descriptor path. |
| `jpeg_sof2_fix` | Adds progressive/SOF2 JPEG dimension recognition. |
| `id3_apic_artwork_support` | Adds JPEG artwork handling for supported ID3v2.3/v2.4 APIC frames, including transformed-frame reading and display requests. |
| `startup_warning_autonext` | Automatically advances past the startup warning. |
| `mp3_open_seek0` | Uses the backend `0 ms` seek path when an MP3 opens, fixing the observed end-of-track cutoff. |
| `map_reminder_interval_365d` | Changes the reminder interval from 28 to 365 days. |
| `map_reminder_text_1_year` | Changes the visible `28 Days` option to `1 Year`. |

## Artwork and Metadata Boundary

- JPEG is the supported display format.
- Baseline and progressive/SOF2 JPEG dimensions are recognized.
- Supported ID3v2.3/v2.4 APIC JPEG frames can be read from their original file
  location when tag transformations prevent the stock path from using the
  stored offset directly.
- The transformed-art reader uses corrected ARM-state pointers for its
  allocate, read, and free veneers. The prior odd pointers entered those ARM
  veneers as Thumb and caused a data abort; the released patch clears those
  three low bits.
- Corrupt or unreadable JPEG artwork is omitted rather than displayed in the
  observed tests. This is not a claim that every malformed image is safe.
- PNG artwork is not supported by the unit, including PNG in an APIC frame.
- Encrypted, linked, malformed, future-version, or guard-exceeding APIC data is
  unsupported and may be omitted while the audio file remains eligible.

### 1 MiB Artwork Limit

The patch set installs a firmware-side artwork limit of exactly 1 MiB
(`1,048,576` bytes, or `0x00100000`). Artwork at or below that size is allowed;
artwork above it is omitted/skipped so the unit does not allocate or read the
oversized image. This applies to the patched Ogg/WMA artwork paths and to
transformed ID3 APIC image data. It is an artwork-payload limit, not an audio
file-size or pixel-dimension limit. The desktop patcher does not scan music
files for this condition; the patched firmware enforces it during media
processing.

## Supported Stock and Patched Hashes

| Region | Stock bytes | Official stock SHA-256 | Expected patched SHA-256 |
|---|---:|---|---|
| NA | `105,662,960` | `257990A6CBA54FDBF428C23ED07AE5A610B5C341B55005948C6F016028176756` | `46D99A29BB0F64C7815412D1A7A3D802400FBD3D5649211122ACDD43489CA74E` |
| AU | `43,815,422` | `56FE3F19D74E314527613881E5AC81D102988672D3EB0A9DE5CAEC74A7E626BE` | `134819C2EB7DD2C6E2739084206D4A1DD6DE551CBD7AFC2942BD06671A4B7E51` |
| EU | `111,065,404` | `31BC511F31AAF99B39BC56A6DB0528FB40AF693A25908AF71830C9E70CDC5360` | `A75756B59BAE0C46D52058560318DE82026208C5CF4E49D1F17D449792C2325C` |
| IN | `61,527,878` | `48ED8CFC4E76643A1A017E8787E232522006C58029326CE243DD3EAF7E6B8E89` | `041AD9254BDC90AF0C9711C61B4EF9ECCA19F72C74FFB5E69B3A67D883B1B5D7` |
| RU | `79,275,178` | `15930479B7BFE69CB730976F3596A856AEB9B7AE1815898FC790F2A18DCC7D5A` | `8DC9DA8E0FA0585A14C6F7F286AB400378EFEAFF6F9CD99F543624A6C7DF21DF` |

Known official Garmin-hosted v4.10 file links:

| Region | URL |
|---|---|
| NA | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/NA/gupdate.gcd> |
| AU | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/AU/gupdate.gcd> |
| EU | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/EU/gupdate.gcd> |
| IN | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/IN/gupdate.gcd> |
| RU | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/RU/gupdate.gcd> |

## Output Safety

- Input, output, and optional report paths must identify different files.
- Canonical-path and existing hard-link aliases are rejected.
- Existing output/report destinations are refused by default.
- CLI replacement requires explicit `--overwrite`.
- Output is staged in the destination directory, flushed, `fsync`-ed, and
  atomically renamed or replaced.
- Published output is read back and verified by length and SHA-256.
- If the GCD succeeds but a requested JSON report fails, the CLI reports
  partial success instead of claiming the GCD patch failed.
- A dry run performs parsing, transformation, checksums, and hash verification
  without writing a GCD.

## Command Line

Show help:

```powershell
FujiV410Patcher-v1.2.1-x86-win7.exe
```

Analyze only:

```powershell
FujiV410Patcher-v1.2.1-x86-win7.exe GUPDATE.GCD --dry-run
```

Patch and optionally write a JSON report:

```powershell
FujiV410Patcher-v1.2.1-x86-win7.exe GUPDATE.GCD -o GUPDATE_patched.gcd
FujiV410Patcher-v1.2.1-x86-win7.exe GUPDATE.GCD -o GUPDATE_patched.gcd --report patch_report.json
```

Use `--overwrite` only when intentionally replacing an existing output/report.
The same options are available through `python fuji_v410_patcher.py`.

## Build Details

The release executable is a one-file x86 Windows GUI application built with:

- Python 3.8.10 x86.
- PyInstaller 6.20.0.
- PE32 machine `0x014C`.
- Windows GUI subsystem `2`, subsystem target `6.0`.

The executable bundles Python and its modules. It targets Windows 7 SP1 or
newer; Windows 7 also requires the Universal CRT update. The GUI has been
smoke-tested on the current Windows environment, but a live Windows 7 x86 test
has not been retained.

Build from a 32-bit Python 3.8 environment:

```powershell
python -m pip install -r requirements-build.txt
.\build_exe.ps1 -PythonPath C:\path\to\32-bit-python-3.8\python.exe
```

The script rejects the wrong Python version, a 64-bit interpreter, or a
PyInstaller version other than 6.20.0.

## Verification Summary

- All five stock regional containers complete a source dry run and produce the
  exact patched hashes listed above.
- The embedded delta test pins span count, changed-byte count, stock/patched
  host hashes, sorted/non-overlapping spans, and feature-offset coverage.
- Public tests cover version/default naming, strict CLI behavior, no-clobber
  atomic writing, explicit replacement, and same-file/hard-link rejection.
- The Windows EXE completes the NA dry run with the expected complete-container
  and patched-host hashes.
- The release archive is checked for integrity, expected contents, forbidden
  firmware-like files, extracted tests, and private/local path leakage.
- Offline verification proves deterministic transformation and file-safety
  behavior. It does not prove AU/EU/IN/RU hardware behavior, universal decoder
  safety, or compatibility with future firmware revisions.

## Update and Recovery Procedure

1. Use firmware for the unit's existing region.
2. Run **Dry-run / Analyze** and stop if verification fails.
3. Generate the patched GCD and place it at `\Garmin\GUPDATE.GCD` on reliable
   FAT32 update media.
4. Park the vehicle and provide stable power. Never update while driving.
5. Attempt the normal update first and follow the unit's prompts.
6. If the unit ignores same-version firmware, the tested NA force-update entry
   is: hold the physical **Voice** button and upper-left touchscreen corner
   while powering on; release after `LOADER` appears.
7. Never remove power or media during the update. After completion, remove or
   rename the update file so it is not offered again.

Keep an unmodified official stock v4.10 file ready. If recovery is necessary,
prepare stock `\Garmin\GUPDATE.GCD` for the correct region and use the same
normal/force-update method. Full power removal may be required if the unit is
stuck in a sleep state. Battery/fuse work should be performed only by someone
comfortable doing it safely.

## Redistribution Boundary

Distribute the patcher, source, documentation, and hashes only. Do not publish
official or patched GCD files, extracted payloads, maps, voices, keys, unlock
files, private logs, or device-owner data.
