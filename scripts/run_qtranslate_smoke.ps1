param(
    [string]$Root = "F:\Codex\QTranslate_diss"
)

$ErrorActionPreference = 'Stop'

Push-Location $Root
try {
    python 'F:\Codex\QTranslate_diss\scripts\patch_qtranslate_links.py'
    python 'F:\Codex\QTranslate_diss\scripts\patch_qtranslate_links.py' --with-accessibility-main
    python 'F:\Codex\QTranslate_diss\scripts\smoke_qtranslate_link_paths.py'
}
finally {
    Pop-Location
}
