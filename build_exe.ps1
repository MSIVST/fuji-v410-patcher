param(
    [string]$PythonPath = ""
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSCommandPath
$sourceRoot = $projectRoot
$workRoot = Join-Path $projectRoot "build"
$distRoot = Join-Path $projectRoot "dist"
$releaseRoot = Join-Path $projectRoot "release-assets"
$entryPoint = Join-Path $sourceRoot "fuji_v410_patcher_app.py"
$releaseName = "FujiV410Patcher-v1.2.1-x86-win7.exe"

if ($PythonPath) {
    $python = [System.IO.Path]::GetFullPath($PythonPath)
} else {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $pythonCommand) {
        throw "Python was not found. Pass a 32-bit Python 3.8 interpreter with -PythonPath."
    }
    $python = $pythonCommand.Source
}

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Python interpreter not found: $python"
}

& $python -c "import struct, sys; assert sys.version_info[:2] == (3, 8); assert struct.calcsize('P') == 4"
if ($LASTEXITCODE -ne 0) {
    throw "The build requires 32-bit Python 3.8."
}

& $python -c "import PyInstaller; assert PyInstaller.__version__ == '6.20.0'"
if ($LASTEXITCODE -ne 0) {
    throw "The build requires PyInstaller 6.20.0. Install requirements-build.txt into the selected interpreter."
}

New-Item -ItemType Directory -Force -Path $workRoot, $distRoot, $releaseRoot | Out-Null

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name FujiV410Patcher `
    --paths $sourceRoot `
    --hidden-import fuji_v410_patcher_gui `
    --distpath $distRoot `
    --workpath $workRoot `
    --specpath $workRoot `
    $entryPoint
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$builtExe = Join-Path $distRoot "FujiV410Patcher.exe"
if (-not (Test-Path -LiteralPath $builtExe -PathType Leaf)) {
    throw "PyInstaller completed without producing $builtExe."
}

$releaseExe = Join-Path $releaseRoot $releaseName
Copy-Item -LiteralPath $builtExe -Destination $releaseExe -Force
$releaseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $releaseExe).Hash

Write-Output "Built $releaseExe"
Write-Output "SHA-256 $releaseHash"
