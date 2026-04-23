param(
    [string]$Root = "F:\Codex\QTranslate_diss",
    [string]$ReleaseDir = "F:\Codex\QTranslate_diss\release\QTranslate_portable_clean",
    [string]$ZipPath = "F:\Codex\QTranslate_diss\release\QTranslate_portable_clean.zip"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $ReleaseDir)) {
    throw "Missing release directory: $ReleaseDir"
}

if (Test-Path $ZipPath) {
    Remove-Item -Force $ZipPath
}

Compress-Archive -Path (Join-Path $ReleaseDir '*') -DestinationPath $ZipPath -Force
Write-Host "Portable archive written to: $ZipPath"
