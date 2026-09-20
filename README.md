# Suzuki Garmin Fuji v4.10 Patcher

An unofficial Windows and Python patcher for official Suzuki Garmin Fuji v4.10
`GUPDATE.GCD` files. It verifies the supplied stock firmware, applies the full
patch set locally, and writes a separate patched file.

No Garmin/Suzuki firmware or patched firmware is included.

## What v1.2.0 Adds

- Ogg/Vorbis playback with unsupported-channel protection.
- Safer rejection of unsupported WMA formats.
- WMA, progressive JPEG, and supported ID3v2.3/v2.4 JPEG cover art.
- Automatic startup-warning advance.
- MP3 end-of-track cutoff fix.
- One-year map-reminder option.
- Strict stock-file validation and safer atomic output writing.

JPEG is the supported artwork format. Corrupt/unreadable JPEG artwork is
omitted; PNG artwork is not supported by the unit.

## Compatibility

The patcher accepts only the pinned official v4.10 NA, AU, EU, IN, and RU
firmware files. North American hardware `39920-61M80` has physical-unit test
evidence. Other regions are verified offline; `39920-61MR1` is unverified.

## Use

1. Download and extract `FujiV410Patcher-v1.2.0-x86-win7.zip`.
2. Obtain the official v4.10 `GUPDATE.GCD` for your region.
3. Run `FujiV410Patcher-v1.2.0-x86-win7.exe`.
4. Select the stock file and run **Dry-run / Analyze** first.
5. If verification succeeds, select **Patch Firmware**.

The source version can be run with Python 3.8 or newer:

```powershell
python fuji_v410_patcher.py GUPDATE.GCD --dry-run
python fuji_v410_patcher.py GUPDATE.GCD -o GUPDATE_patched.gcd
```

## Important

Firmware modification can brick the unit and may void warranties. Use stable
power, keep stock recovery firmware available, never interrupt an update, and
do not cross-flash regional firmware unless you understand the consequences.

See [Technicals.md](Technicals.md) for exact hashes, patch behavior, build and
verification details, command-line options, and update/recovery instructions.

This project is not affiliated with, endorsed by, or supported by Garmin or
Suzuki.
