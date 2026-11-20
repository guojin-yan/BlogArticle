[CmdletBinding()]
param([string] $HipRoot = $env:HIP_PATH, [string] $OutputRoot, [int] $Rounds = 5)
$ErrorActionPreference = 'Stop'
if ($Rounds -lt 3) { throw 'Use at least three independent processes.' }
if (!$HipRoot) { $HipRoot = Read-Host 'ROCm 10.1 HIP root (bin and lib)' }
$root = (Resolve-Path -LiteralPath $HipRoot).Path
$env:HIP_PATH = $root
$env:ROCM_PATH = $root
$env:PATH = "$root/bin;$root/lib/llvm/bin;$env:PATH"
$env:HIP_DEVICE_LIB_PATH = "$root/lib/llvm/amdgcn/bitcode"
$env:ROCBLAS_TENSILE_LIBPATH = "$root/bin/rocblas/library"
$env:HIPBLASLT_TENSILE_LIBPATH = "$root/bin/hipblaslt/library/gfx1100"
if (!$OutputRoot) { $OutputRoot = Join-Path (Split-Path -Parent $PSScriptRoot) '.validation/round2' }
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)
New-Item -ItemType Directory -Force -Path "$OutputRoot/logs", "$OutputRoot/results", "$OutputRoot/inputs" | Out-Null
$model = "$OutputRoot/inputs/yolox_nano.onnx"
if (!(Test-Path -LiteralPath $model)) {
    Invoke-WebRequest 'https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_nano.onnx' -OutFile $model
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $model).Hash.ToLowerInvariant() -ne 'c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d') { throw 'Model SHA256 mismatch' }
dotnet build "$PSScriptRoot/MigraphxCompute" -c Release --nologo *> "$OutputRoot/logs/build.txt"
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$assembly = "$PSScriptRoot/MigraphxCompute/bin/Release/net10.0/MigraphxCompute.dll"
$environment = [ordered]@{
    date = (Get-Date).ToString('o'); windows = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber
    driver = Get-CimInstance Win32_VideoController | Select-Object Name,DriverVersion,DriverDate
    cpu = Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
    powershell = $PSVersionTable.PSVersion.ToString(); dotnet = (& dotnet --version)
    architecture = 'gfx1100'; architectureSource = 'Same W7900 hardware as issue1; requested HIPRTC target; no new independent hardware gfx detector'
    cpuOrt = '1.23.2; default thread counts; sequential graph; CPU provider only'
    clockPower = 'Not locked'; background = 'Interactive desktop; no isolation, browsers and desktop apps remain open'
    cacheCold = 'NOT TESTED'; processIsolation = 'Each round is a new dotnet process on the same physical Windows host'
    baselineCommit = (& git -C (Split-Path -Parent $PSScriptRoot) rev-parse HEAD)
}
$environment | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 "$OutputRoot/environment.json"
for ($round = 1; $round -le $Rounds; $round++) {
    $seed = 20261120 + $round
    $before = Get-Process | Sort-Object CPU -Descending | Select-Object -First 12 ProcessName,CPU,WorkingSet64
    $before | ConvertTo-Json | Set-Content -Encoding utf8 "$OutputRoot/results/background-before-$round.json"
    "dotnet <examples>/MigraphxCompute/bin/Release/net10.0/MigraphxCompute.dll --mode ablation --model <output>/inputs/yolox_nano.onnx --output <output>/results/benchmark-$round.json --seed $seed" | Add-Content "$OutputRoot/commands.txt"
    Write-Host "Round $round/$Rounds; seed=$seed; independent process"
    & dotnet $assembly --mode ablation --model $model --output "$OutputRoot/results/benchmark-$round.json" --seed $seed *> "$OutputRoot/logs/benchmark-$round.log"
    $code = $LASTEXITCODE
    @{ round = $round; exitCode = $code; finished = (Get-Date).ToString('o') } | ConvertTo-Json | Set-Content "$OutputRoot/results/exit-$round.json"
    if ($code -ne 0) { Write-Warning "Round $round failed; evidence retained" }
}
Write-Host 'All requested rounds finished; inspect every result and failure, not only the fastest.'
