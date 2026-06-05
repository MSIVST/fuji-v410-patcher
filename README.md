# Suzuki Garmin Fuji v4.10 Patcher

Unofficial patcher for official Suzuki Garmin Fuji v4.10 `GUPDATE.GCD` files.

<img src="https://i.imgur.com/dq9ab5Y.jpeg" width="400">

## WHY?

This patcher exists to make three small, targeted quality-of-life changes while keeping the official Suzuki Garmin Fuji v4.10 firmware structure intact.

- **Startup [warning](https://i.imgur.com/ZlZu8yr.jpeg):** the factory warning page requires a manual `Agree` press on every startup. This patch automatically advances through the existing startup flow so the unit lands on the normal last-used screen.
- **MP3 cutoff:** Fresh MP3 playback could advance before the playback backend drained the final audio tail. This would cut-off about ~250ms audio from the end of the currently-playing file, before advancing to the next track.
	
	'Seek' or 'resume' playback did not show the same cutoff.
	
	This patch makes fresh MP3 open use the existing `0 ms` backend seek path so that it matches Seek/Resume behaviors.
	
- **Map reminder:** the factory map-update reminder returns every 28 days. This patch keeps the reminder enabled, but changes the interval to 365 days and updates the visible option text to `1 Year`.

This tool does **not** include Garmin or Suzuki firmware. It requires the user to supply an official Suzuki Garmin Fuji v4.10 `GUPDATE.GCD`, verifies that file, applies small byte patches locally, fixes visible GCD checksum blocks, and writes a patched output file.

## Patch Set

The patcher applies four small changes inside the `0x02BD` host firmware payload:

| Patch | `fw_all` offset | Purpose |
|---|---:|---|
| `startup_warning_autonext` | `0x0027102E` | Automatically advances past the startup warning using the existing startup dispatcher path. |
| `mp3_open_seek0` | `0x00778300` | Forces fresh MP3 playback to use the existing backend seek path with `0 ms`, matching the seek/resume path that drains the audio tail correctly. |
| `map_reminder_interval_365d` | `0x00175C6C` | Changes the map reminder snooze interval from 28 days to 365 days. |
| `map_reminder_text_1_year` | `0x00DBDC7C` | Changes the visible reminder option from `28 Days` to `1 Year`. |

## Update Path

The current release focuses only on the startup warning, MP3 cutoff, and map reminder interval. Future work such as WMA stability fixes or Bluetooth reconnect-message behavior should be added as separate, documented patch modules rather than mixed silently into this release.

See [docs/UPDATE_POLICY.md](docs/UPDATE_POLICY.md) for the proposed update process, versioning rules, and testing checklist for future WMA/BT/media fixes.

## Requirements

For the standalone Windows EXE release:

- Best-effort Windows 7/8/8.1/10/11 support.
- Built as a 32-bit Windows executable with Python 3.8.10 and PyInstaller 6.20.0. No Python install required.
- The 32-bit executable should run on both 32-bit Windows and normal 64-bit Windows.
- Localized Windows installs should be OK; the CLI was tested with Unicode paths containing Cyrillic and Devanagari characters.
- An official Suzuki Garmin Fuji v4.10 `GUPDATE.GCD`.
- Tested on a North American Suzuki Garmin Fuji unit marked `39920-61M80`. Compatibility with `39920-61MR1` is **unknown**.

For the source Python release:

- Python 3.8 or newer.
- An official Suzuki Garmin Fuji v4.10 `GUPDATE.GCD`.
- A compatible Suzuki Garmin Fuji unit.
- A known-good stock recovery/update process before testing.

No third-party Python packages are required.

## Supported Official v4.10 Inputs

The tool recognizes these stock full-file SHA-256 hashes:

| Region | Stock file size | Stock SHA-256 |
|---|---:|---|
| NA | `105,662,960` | `257990A6CBA54FDBF428C23ED07AE5A610B5C341B55005948C6F016028176756` |
| AU | `43,815,422`  | `56FE3F19D74E314527613881E5AC81D102988672D3EB0A9DE5CAEC74A7E626BE` |
| EU | `111,065,404` | `31BC511F31AAF99B39BC56A6DB0528FB40AF693A25908AF71830C9E70CDC5360` |
| IN | `61,527,878`  | `48ED8CFC4E76643A1A017E8787E232522006C58029326CE243DD3EAF7E6B8E89` |
| RU | `79,275,178`  | `15930479B7BFE69CB730976F3596A856AEB9B7AE1815898FC790F2A18DCC7D5A` |

The `0x02BD` host firmware payload is identical across the tested AU/EU/IN/RU v4.10 files:

```text
F566A42E1EA7A2CACD243E884A721209C024FB370635194F3C27B8B66928D3B6
```

## Official Firmware Links

This patcher does not include firmware. Users must supply their own official Suzuki Garmin Fuji v4.10 `GUPDATE.GCD`.

Known official Garmin-hosted v4.10 links:

| Region | Official firmware URL |
|---|---|
| AU | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/AU/gupdate.gcd> |
| EU | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/EU/gupdate.gcd> |
| IN | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/IN/gupdate.gcd> |
| NA | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/NA/gupdate.gcd> |
| RU | <https://static.garmincdn.com/autoOem/suzuki/software/4.10/RU/gupdate.gcd> |

## Windows GUI Usage

Standalone EXE release:

1. Extract the zip.
2. Double-click `FujiV410Patcher.exe`.
3. Select an official `GUPDATE.GCD` input.
4. Select an output file.
5. Click `Dry-run / Analyze` first.
6. If verification succeeds, click `Patch Firmware`.

The standalone EXE is built as a Windows GUI application, so double-clicking it should not open a separate command window. If launched from PowerShell or Command Prompt with no arguments, it prints command-line usage instead of opening the GUI.

Source Python release:

For a simple Windows app experience:

1. Extract the zip.
2. Double-click `Launch Fuji Patcher GUI.cmd`.
3. Select an official `GUPDATE.GCD`.
4. Click `Dry-run / Analyze` first.
5. If verification succeeds, click `Patch Firmware`.

The GUI writes the patched GCD. JSON report output is optional and is off by default.

If `.cmd` launching fails, install Python 3 for Windows from python.org and make sure the `py` launcher or `python.exe` is available.

## Step-by-Step Firmware Update / Force Update

These steps describe the update method tested on a North American `39920-61M80` Suzuki Garmin Fuji unit. Other Fuji units may behave differently.

### 1. Before Flashing

1. Make sure the vehicle is parked safely. Do not perform firmware work while driving.
2. Use stable power. Avoid flashing with a weak vehicle battery.
3. Keep an unmodified official stock v4.10 `GUPDATE.GCD` available for recovery.
4. Use the same region firmware that is already appropriate for your unit unless you intentionally understand the risks of changing regions.
5. Read the entire procedure before starting.

### 2. Create the Patched Firmware File

1. Download the official v4.10 `GUPDATE.GCD` for your region from the links above.
2. Extract this patcher package on a Windows PC.
3. Double-click `FujiV410Patcher.exe`.
4. Select an official `GUPDATE.GCD` input.
5. Select an output file.
6. Click `Dry-run / Analyze` first.
7. If verification succeeds, click `Patch Firmware`.
8. Do not continue if the patcher reports an error or refuses the file.

### 3. Prepare the Update Media

1. Use a small, reliable SD card. USB media may work on some units, but the tested method uses SD.
2. Format it as `FAT32` if possible.
3. Remove any older update files from the media.
4. Create a folder named exactly `Garmin` in the root of the SD card.
5. Copy the patched file into the `Garmin` folder.
6. Rename the patched file exactly to `GUPDATE.GCD`.
7. Confirm the final path is `\Garmin\GUPDATE.GCD` on the SD card.
8. Safely eject the media from Windows.

### 4. Force Firmware Update Method

As the stock & patched firmware both keep the 'v4.10' string, we need to force a firmware update on the unit.
(The unit ignores the file, or says the GCD is 'not newer than the current software' when sd card inserted).

The tested force-update method is:

1. Power the vehicle/unit off.
2. Insert the prepared SD card containing `\Garmin\GUPDATE.GCD`.
3. Hold the physical `Voice` button.
4. While holding `Voice`, press and hold the upper-left corner of the [touchscreen](https://i.imgur.com/oTFXC3r.jpeg).
5. Power the unit on while continuing to hold both the `Voice` button and the upper-left touchscreen corner.
6. Keep holding both until `LOADER` is displayed on the unit.
7. Allow the update to run, then wait for the unit to reboot completely.
8. After the update finishes, remove the SD card or delete/rename `\Garmin\GUPDATE.GCD`.

### 6. Recovery Back to Stock Firmware

If the update fails, the unit hangs, or you want to return to stock:

1. Remove the update media.
2. Power-cycle the unit.
3. If the unit still does not boot normally, prepare a media device with the unmodified stock v4.10 `GUPDATE.GCD`.
4. Repeat the force/recovery update method with the stock firmware.
5. If the unit appears stuck in a sleep state, fully remove power from the radio/navigation unit before retrying. Use the vehicle battery disconnect or appropriate radio/navigation fuse only if you are comfortable doing so.

### 7. Update Notes

- `GUPDATE.GCD` naming may matter on this unit. Use the uppercase filename shown above.
- The update file must be inside the `Garmin` folder, not loose in the SD card root.
- Use only one update file at a time.
- The patched file should be generated from the same region firmware you intend to install.
- Do not cross-flash regional firmware unless you understand the map, language, radio, and resource differences.

## Command-Line Usage

Standalone EXE release:

Show help from PowerShell or Command Prompt:

```powershell
FujiV410Patcher.exe
```

Dry-run first:

```powershell
FujiV410Patcher.exe GUPDATE.GCD --dry-run
```

Patch a file:

```powershell
FujiV410Patcher.exe GUPDATE.GCD -o GUPDATE_patched.gcd
```

Optional JSON report:

```powershell
FujiV410Patcher.exe GUPDATE.GCD -o GUPDATE_patched.gcd --report patch_report.json
```

Note: the EXE is intentionally built as a Windows GUI application so double-clicking it does not open a command window. When used from PowerShell or Command Prompt, it can print usage and run command-line patching, but the shell may return to the prompt before a long patch operation has fully finished. If you want fully blocking console behavior, use the source Python command-line mode below.

Source Python release:

Dry-run first:

```powershell
python fuji_v410_patcher.py GUPDATE.GCD --dry-run
```

Patch a file:

```powershell
python fuji_v410_patcher.py GUPDATE.GCD -o GUPDATE_patched.gcd --report patch_report.json
```

If the input hash is not in the known list but the host payload is still the expected stock v4.10 payload, the tool can be run with:

```powershell
python fuji_v410_patcher.py GUPDATE.GCD -o GUPDATE_patched.gcd --allow-unknown-hash
```

## "Allow Unknown Full-File Hash" option

By default, the patcher only accepts official v4.10 GCD files whose full-file SHA-256 is in the known NA/AU/EU/IN/RU list.

`--allow-unknown-hash` bypasses only that outer full-file hash allow-list. It does **not** blindly patch arbitrary firmware.

Even with this option enabled, the patcher still requires:

- Valid Garmin GCD structure and checksum blocks.
- The expected Suzuki Fuji v4.10 host firmware section metadata.
- The embedded host firmware payload SHA-256 to match the known stock v4.10 `fw_all` payload.
- The exact expected original bytes at every patch offset.

This option is useful only if someone has an official v4.10 GCD whose outer container differs, while the internal host firmware payload is still identical to the known stock v4.10 payload.

Keep this option off unless you know exactly why you need it. It will not make v2.8, v3.9, altered, or incompatible firmware safe to patch.

## Expected Patched Hashes

The patcher was tested against the known stock files and produced these output SHA-256 hashes:

| Region | Patched SHA-256 |
|---|---|
| NA | `0F4531FB300E2AC03D13AB1CCEB587AAD24F2D8E847F1B640844D4E9C98CC901` |
| AU | `0E2DE58385EE6B7AC354883297F59312E3D1D9C9A5ACB196F25682B0AAE417E0` |
| EU | `5A59F45A31645FD41B6BD2789E433677250389E7183A7262777FD96278F89535` |
| IN | `99B7529D52067C87CC9A451115A3DDFC80488CC084414EED7668C686BE72F792` |
| RU | `18D6A45CF74E18B135BEA8EAD061A4F5AABA7BF7113225F4B0E8C18D63A8E804` |

## Safety Notes

- This is unofficial firmware modification research.
- Use at your own risk.
- This may void warranties.
- A failed update may brick the unit.
- Do not test firmware updates while driving.
- Keep a known-good stock firmware and recovery/update method available.
- Do not cross-flash regional firmware unless you intentionally want that region's bundled resources and understand the risks.

## Redistribution Notes

This package intentionally contains no Garmin or Suzuki firmware. The recommended public-release model is to share this patcher, the technical notes, and hashes, while requiring each user to obtain their own official firmware.

Avoid uploading complete patched `GUPDATE.GCD` files publicly. A disclaimer does not automatically solve copyright, warranty, safety, or liability concerns.

## Not Affiliated

This tool is not affiliated with, endorsed by, or supported by Garmin or Suzuki. Garmin and Suzuki names and trademarks belong to their respective owners.
