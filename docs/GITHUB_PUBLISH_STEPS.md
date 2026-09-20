# GitHub Publish Steps

These steps assume the GitHub CLI (`gh`) is installed and authenticated.

## 1. Review Locally

```powershell
git status
git diff --check
```

Confirm that no firmware files are staged:

```powershell
git ls-files | Select-String -Pattern '\\.(gcd|GCD|rgn|RGN|bin|BIN|img|IMG|gma|GMA|unl|UNL)$'
```

## 2. Create Repository

Replace `YOUR_GITHUB_NAME` with your account or organization.

```powershell
gh repo create YOUR_GITHUB_NAME/fuji-v410-patcher --public --source . --remote origin --push
```

Suggested repository description:

```text
Unofficial patcher for official Suzuki Garmin Fuji v4.10 GUPDATE.GCD files. No firmware included.
```

Suggested topics:

```text
garmin suzuki fuji firmware-patcher infotainment mp3 automotive
```

## 3. Create Release

```powershell
git tag -a v1.2.0 -m "Fuji v4.10 patcher v1.2.0"
git push origin v1.2.0
gh release create v1.2.0 release-assets/FujiV410Patcher-v1.2.0-x86-win7.zip --title "Fuji v4.10 Patcher v1.2.0" --notes-file docs/releases/v1.2.0.md
```

## 4. Keep Firmware Out of GitHub

Do not upload:

- Official `GUPDATE.GCD`.
- Patched `GUPDATE.GCD`.
- Extracted `fw_all.bin`, `boot.bin`, `LDR.bin`, or region payloads.
- Maps, voices, unlock files, keys, logs with personal data, or proprietary resources.
