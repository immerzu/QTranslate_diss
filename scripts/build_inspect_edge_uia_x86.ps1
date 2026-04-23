param(
    [string]$Configuration = "release"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$sdk = "10.0.26100.0"
$clang = "C:\Program Files\LLVM\bin\clang-cl.exe"
$source = Join-Path $root "native\inspect_edge_uia_x86.cpp"
$outDir = Join-Path $root "tmp_patch"
$outExe = Join-Path $outDir "inspect_edge_uia_x86.exe"

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$includeArgs = @(
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\ucrt",
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\shared",
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\um",
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\winrt",
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\cppwinrt"
)

$libArgs = @(
    "/link",
    "/LIBPATH:C:\Program Files (x86)\Windows Kits\10\Lib\$sdk\ucrt\x86",
    "/LIBPATH:C:\Program Files (x86)\Windows Kits\10\Lib\$sdk\um\x86",
    "user32.lib",
    "ole32.lib",
    "oleaut32.lib",
    "UIAutomationCore.lib"
)

$commonArgs = @(
    "/nologo",
    "/std:c++17",
    "/EHsc",
    "/DUNICODE",
    "/D_UNICODE",
    "/DWIN32_LEAN_AND_MEAN",
    "/D_WIN32_WINNT=0x0601",
    "/MT",
    "/clang:--target=i686-pc-windows-msvc",
    $source,
    "/Fe:$outExe"
)

if ($Configuration -eq "debug") {
    $commonArgs += "/Od", "/Zi"
} else {
    $commonArgs += "/O2"
}

& $clang @commonArgs @includeArgs @libArgs
Write-Output "Built: $outExe"
