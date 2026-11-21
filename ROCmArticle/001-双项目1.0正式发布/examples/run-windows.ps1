[CmdletBinding()]
param(
    [string] $HipRoot = $env:HIP_PATH,
    [string] $Architecture = 'gfx1100',
    [ValidateSet('verify', 'benchmark', 'trace', 'ablation', 'cache', 'detect', 'doctor')][string] $Mode = 'verify',
    [string] $ModelPath,
    [string] $OutputPath,
    [string] $CachePath,
    [ValidateSet('parsed','compiled')][string] $CacheKind = 'parsed',
    [string] $ImagePath,
    [int] $Seed = 20261120,
    [switch] $CheckOnly
)
$ErrorActionPreference = 'Stop'
if ($CheckOnly) { $Mode = 'doctor' }
$articleRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($HipRoot)) {
    $HipRoot = Read-Host 'Enter the ROCm 10.1 HIP installation directory (containing bin and lib)'
}
if ([string]::IsNullOrWhiteSpace($HipRoot)) { throw 'Specify -HipRoot or configure HIP_PATH.' }
$rocmHipRoot = [System.IO.Path]::GetFullPath($(if (Test-Path -LiteralPath $HipRoot) { (Resolve-Path -LiteralPath $HipRoot).Path } else { $HipRoot }))
if ($Mode -ne 'doctor' -and !(Test-Path -LiteralPath "$rocmHipRoot/bin")) { throw 'HIP SDK bin directory is missing. Run -CheckOnly for diagnostics.' }
if ($Architecture -notmatch '^gfx[0-9a-f]+$') { throw 'Specify the actual GPU architecture, for example gfx1100.' }
$env:HIP_PATH = $rocmHipRoot
$env:ROCM_PATH = $rocmHipRoot
$env:PATH = "$(Join-Path $rocmHipRoot 'bin');$(Join-Path $rocmHipRoot 'lib\llvm\bin');$env:PATH"
$env:HIP_DEVICE_LIB_PATH = Join-Path $rocmHipRoot 'lib\llvm\amdgcn\bitcode'
# Keep native separators: the tested Windows hipBLASLt loader crashes on forward-slash paths.
$env:ROCBLAS_TENSILE_LIBPATH = Join-Path $rocmHipRoot 'bin\rocblas\library'
$env:HIPBLASLT_TENSILE_LIBPATH = Join-Path $rocmHipRoot "bin\hipblaslt\library\$Architecture"
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
if ($Mode -eq 'ablation') { $computeArgs += @('--seed', "$Seed") }
if ($CachePath) { $computeArgs += @('--cache', [System.IO.Path]::GetFullPath($CachePath), '--cache-kind', $CacheKind) }
if ($ImagePath) { $computeArgs += @('--image', (Resolve-Path -LiteralPath $ImagePath).Path) }
if ($Mode -eq 'doctor') {
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent ([System.IO.Path]::GetFullPath($OutputPath))) | Out-Null
    $inventory = [ordered]@{
        date = (Get-Date).ToString('o'); powershell = $PSVersionTable.PSVersion.ToString()
        sdks = @(& dotnet --list-sdks); gpuDriver = @(Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate)
        os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber
        scope = 'Inventory only; GPU gfx is not inferred from the product name. No global PATH, driver or dependency installation changes.'
    }
    $inventory | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 -LiteralPath "$OutputPath.inventory.json"
    $env:ARTICLE_DOCTOR_INVENTORY = [System.IO.Path]::GetFullPath("$OutputPath.inventory.json")
}
& dotnet run --project "$PSScriptRoot/MigraphxCompute" -c Release -- @computeArgs
$computeExit = $LASTEXITCODE
if ($computeExit -ne 0) { throw "MIGraphX $Mode failed with exit code $computeExit; inspect $OutputPath and the log" }
