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
- [ ] The release ZIP contains only the EXE, README, license, and source files.

## Release Asset

- [ ] ZIP is uploaded as a GitHub Release asset.
- [ ] ZIP SHA-256 is included in release notes.
- [ ] Release notes repeat that no firmware is included.
- [ ] Release is marked prerelease if it contains experimental WMA/BT/media behavior.

## Suggested Release Commands

```powershell
git status
git tag -a v1.0.0 -m "Fuji v4.10 patcher v1.0.0"
git push origin main --tags
gh release create v1.0.0 release-assets/FujiV410Patcher_x86_v1_20260605.zip --title "FujiV410Patcher x86 v1.0.0" --notes-file docs/releases/v1.0.0.md
```
