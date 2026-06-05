# Contributing

This project is intentionally conservative. Firmware patching can brick hardware, so changes should be small, reviewable, and backed by testing.

## Ground Rules

- Do not submit Garmin/Suzuki firmware, patched `GUPDATE.GCD` files, extracted firmware payloads, maps, voices, logos, keys, or other copyrighted assets.
- Do not submit private logs that contain serial numbers, personal locations, phone identifiers, Bluetooth pairing data, or owner-specific files.
- Keep each patch as a separate named module with documented expected bytes, replacement bytes, target offset, and verification behavior.
- Do not silently change existing patches under the same release version.

## Pull Request Checklist

- The patcher still refuses unsupported firmware by default.
- The patch verifies exact expected original bytes before writing.
- `--dry-run` succeeds on known stock firmware.
- The README/changelog explain the user-visible behavior change.
- Any device testing is documented with unit part number, region, firmware version, and recovery path.

## Good Future Contributions

- Better test reports across AU/EU/IN/RU/NA units.
- Clear diagnostics for unsupported or unknown GCD files.
- Separately toggleable WMA or Bluetooth behavior patches after device testing.
- Build/release automation that does not bundle firmware.
