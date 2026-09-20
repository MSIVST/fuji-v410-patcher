# GitHub Release Checklist

Use this before publishing a new public release.

## Repository Contents

- [ ] Source files are present.
- [ ] README is current.
- [ ] CHANGELOG is current.
- [ ] LICENSE is present.
- [ ] No official Garmin/Suzuki firmware is committed.
- [ ] No patched firmware is committed.
- [ ] No extracted firmware payloads are committed.
- [ ] No private logs, serial numbers, personal paths, or API keys are committed.

## Build Checks

- [ ] `python fuji_v410_patcher.py GUPDATE.GCD --dry-run` succeeds on a known stock input.
- [ ] Generated patched hash matches the README for at least one known stock input.
- [ ] Windows GUI opens by double-click.
- [ ] PowerShell no-argument launch prints usage.
- [ ] The release ZIP contains only the EXE, README, Technicals, Security, and Changelog files.

## Release Asset

- [ ] ZIP is uploaded as a GitHub Release asset.
- [ ] ZIP SHA-256 is included in release notes.
- [ ] Release notes repeat that no firmware is included.
- [ ] Hardware-tested and offline-only compatibility claims remain distinct.

## Suggested Release Commands

Review the branch, commit it, and merge it before tagging. Then create the
release from the exact reviewed commit:

```powershell
git status
git tag -a v1.2.1 -m "Fuji v4.10 patcher v1.2.1"
git push origin v1.2.1
gh release create v1.2.1 release-assets/FujiV410Patcher-v1.2.1-x86-win7.zip --title "Fuji v4.10 Patcher v1.2.1" --notes-file docs/releases/v1.2.1.md
```
