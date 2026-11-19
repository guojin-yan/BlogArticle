[CmdletBinding()]
param(
    [string] $HipRoot = $env:HIP_PATH,
    [string] $Architecture = 'gfx1100',
    [ValidateSet('verify', 'benchmark', 'trace')][string] $Mode = 'verify',
    [string] $ModelPath,
    [string] $OutputPath
)
$ErrorActionPreference = 'Stop'
$articleRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($HipRoot)) {
    $HipRoot = Read-Host 'Enter the ROCm 10.1 HIP installation directory (containing bin and lib)'
}
if ([string]::IsNullOrWhiteSpace($HipRoot)) { throw 'Specify -HipRoot or configure HIP_PATH.' }
$rocmHipRoot = (Resolve-Path -LiteralPath $HipRoot).Path
if (!(Test-Path -LiteralPath "$rocmHipRoot/bin")) { throw 'HIP SDK bin directory is missing.' }
if ($Architecture -notmatch '^gfx[0-9a-f]+$') { throw 'Specify the actual GPU architecture, for example gfx1100.' }
$env:HIP_PATH = $rocmHipRoot
$env:ROCM_PATH = $rocmHipRoot
$env:PATH = "$rocmHipRoot/bin;$rocmHipRoot/lib/llvm/bin;$env:PATH"
$env:HIP_DEVICE_LIB_PATH = "$rocmHipRoot/lib/llvm/amdgcn/bitcode"
$env:ROCBLAS_TENSILE_LIBPATH = "$rocmHipRoot/bin/rocblas/library"
$env:HIPBLASLT_TENSILE_LIBPATH = "$rocmHipRoot/bin/hipblaslt/library/$Architecture"
if (!$OutputPath) { $OutputPath = "$articleRoot/.validation/compute-$Mode.json" }
if ($Mode -eq 'verify' -and !$ModelPath) {
    & dotnet run --project "$PSScriptRoot/HipHello" -c Release
    if ($LASTEXITCODE -ne 0) { throw 'Device enumeration failed.' }
    & dotnet run --project "$PSScriptRoot/HipVectorAdd" -c Release -- --arch $Architecture
    if ($LASTEXITCODE -ne 0) { throw 'VectorAdd failed.' }
    Push-Location "$PSScriptRoot/MigraphxHello"
    try {
        & dotnet run -c Release
        if ($LASTEXITCODE -ne 0) { throw 'Identity smoke check failed.' }
    } finally { Pop-Location }
}
$computeArgs = @('--mode', $Mode, '--arch', $Architecture, '--output', $OutputPath)
if ($ModelPath) { $computeArgs += @('--model', (Resolve-Path -LiteralPath $ModelPath).Path) }
& dotnet run --project "$PSScriptRoot/MigraphxCompute" -c Release -- @computeArgs
if ($LASTEXITCODE -ne 0) { throw "MIGraphX compute failed with exit code $LASTEXITCODE" }
