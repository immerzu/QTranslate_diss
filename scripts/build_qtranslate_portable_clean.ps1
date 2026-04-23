param(
    [string]$Root = "F:\Codex\QTranslate_diss",
    [string]$OutputDir = "F:\Codex\QTranslate_diss\release\QTranslate_portable_clean"
)

$ErrorActionPreference = 'Stop'

$source = Join-Path $Root 'QTranslate.6.9.0'
$finalExe = Join-Path $source 'QTranslate.output_links.exe'
if (-not (Test-Path $finalExe)) {
    throw "Missing final executable: $finalExe"
}

if (Test-Path $OutputDir) {
    Remove-Item -Recurse -Force $OutputDir
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$keep = @(
    'Data',
    'Locales',
    'Plugins',
    'Resources',
    'Services',
    'Themes',
    'bass.dll',
    'License.rtf'
)

foreach ($name in $keep) {
    $srcItem = Join-Path $source $name
    $dstItem = Join-Path $OutputDir $name
    if (-not (Test-Path $srcItem)) {
        throw "Missing required release item: $srcItem"
    }
Copy-Item -Recurse -Force $srcItem $dstItem
}

Copy-Item -Force $finalExe (Join-Path $OutputDir 'QTranslate.exe')

$servicesOut = Join-Path $OutputDir 'Services'
Get-ChildItem -LiteralPath $servicesOut -File -Filter '*.rar' -ErrorAction SilentlyContinue |
    Remove-Item -Force

$optionsPath = Join-Path $OutputDir 'Data\Options.json'
if (Test-Path $optionsPath) {
    $options = Get-Content -Raw -Path $optionsPath | ConvertFrom-Json
    if ($options.Contents) {
        $options.Contents.EditSource = ""
        $options.Contents.EditTranslation = ""
        $options.Contents.EditBackTranslation = ""
    }
    if ($options.General) {
        $options.General.LanguageFrom = 1
        $options.General.LanguageTo = 23
        $options.General.LocaleFoderName = "German"
    }
    $options.LanguagePairs = @(@(1, 23), @(23, 1))
    $options | ConvertTo-Json -Depth 32 | Set-Content -Encoding UTF8 -Path $optionsPath
}

$historyPath = Join-Path $OutputDir 'Data\History.json'
if (Test-Path $historyPath) {
    '[]' | Set-Content -Encoding UTF8 -Path $historyPath
}

Get-ChildItem -Path (Join-Path $OutputDir 'Data') -Filter 'Options.before_*.json' -File -ErrorAction SilentlyContinue |
    Remove-Item -Force

@'
QTranslate Portable Clean

This portable package contains the combined stable build:
- clipboard/HTML link preservation
- browser/UIA link preservation
- output RichEdit link rendering support

Start:
- Run QTranslate.exe

Verified with:
- scripts\run_qtranslate_smoke.ps1

Note:
- When testing, run only one QTranslate instance at a time. The release uses shared Data\Options.json and Data\History.json files.
'@ | Set-Content -Encoding ASCII (Join-Path $OutputDir 'README.txt')

@(
    'QTranslate.patched.exe',
    'QTranslate.output_links.exe',
    'QTranslate.accessibility.default_uia.exe',
    'QTranslate.accessibility.delegate.current.exe',
    'QTranslate.accessibility.delegate.exe',
    'QTranslate.accessibility.experimental.exe',
    'QTranslate.accessibility.name_only.exe',
    'QTranslate.accessibility.noop.current.exe',
    'QTranslate.accessibility.noop.exe',
    'QTranslate.accessibility.uia_point.exe'
) | ForEach-Object {
    $path = Join-Path $OutputDir $_
    if (Test-Path $path) {
        Remove-Item -Force $path
    }
}

Write-Host "Portable release written to: $OutputDir"
