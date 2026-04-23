param()

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$sdk = "10.0.26100.0"
$clang = "C:\Program Files\LLVM\bin\clang-cl.exe"
$objdump = "C:\Program Files\LLVM\bin\llvm-objdump.exe"
$source = Join-Path $root "native\uia_point_pipeline.cpp"
$outDir = Join-Path $root "tmp_patch"
$outAsm = Join-Path $outDir "uia_point_pipeline_x86.asm"
$outObj = Join-Path $outDir "uia_point_pipeline_x86.obj"

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$includeArgs = @(
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\ucrt",
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\shared",
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\um",
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\winrt",
    "/I", "C:\Program Files (x86)\Windows Kits\10\Include\$sdk\cppwinrt"
)

$args = @(
    "/nologo",
    "/std:c++17",
    "/EHsc",
    "/c",
    "/O2",
    "/GS-",
    "/GR-",
    "/DUNICODE",
    "/D_UNICODE",
    "/DWIN32_LEAN_AND_MEAN",
    "/clang:--target=i686-pc-windows-msvc",
    $source,
    "/Fo$outObj"
)

& $clang @args @includeArgs
& $objdump -d --no-show-raw-insn $outObj | Set-Content -Path $outAsm -Encoding ASCII
Write-Output "Built: $outAsm"
