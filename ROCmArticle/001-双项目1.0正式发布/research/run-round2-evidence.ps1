[CmdletBinding()]
param([Parameter(Mandatory)][string] $HipRoot, [Parameter(Mandatory)][string] $CacheRoot,
      [string] $OutputRoot, [string] $Python = 'python')
$ErrorActionPreference = 'Stop'
$article = Split-Path -Parent $PSScriptRoot
$archived = Join-Path $PSScriptRoot 'validation/round2'
if (!$OutputRoot) { $OutputRoot = Join-Path $article '.validation/evidence-new' }
$r2 = [IO.Path]::GetFullPath($OutputRoot)
$CacheRoot = [IO.Path]::GetFullPath($CacheRoot)
if (Test-Path -LiteralPath $r2) { throw 'Choose a new output directory; historical evidence is not overwritten.' }
if (Test-Path -LiteralPath $CacheRoot) { throw 'Choose a new cache directory to exercise a miss.' }
if ($CacheRoot -match '[^\x00-\x7F]') { throw 'Use ASCII cache path; Unicode save failure is documented separately.' }
New-Item -ItemType Directory -Force -Path "$r2/logs", "$r2/results", "$r2/inputs" | Out-Null
Copy-Item -LiteralPath "$archived/inputs/yolox_nano.onnx", "$archived/inputs/astronaut.png" -Destination "$r2/inputs"
$root = (Resolve-Path -LiteralPath $HipRoot).Path
$env:HIP_PATH = $root; $env:ROCM_PATH = $root
$env:PATH = "$root/bin;$root/lib/llvm/bin;$env:PATH"
$env:HIP_DEVICE_LIB_PATH = "$root/lib/llvm/amdgcn/bitcode"
$env:ROCBLAS_TENSILE_LIBPATH = "$root/bin/rocblas/library"
$env:HIPBLASLT_TENSILE_LIBPATH = "$root/bin/hipblaslt/library/gfx1100"
dotnet build "$article/examples/MigraphxCompute" -c Release --nologo *> "$r2/logs/build-evidence.txt"
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$assembly = "$article/examples/MigraphxCompute/bin/Release/net10.0/MigraphxCompute.dll"
$native = "$article/examples/MigraphxCompute/bin/Release/net10.0/runtimes/win-x64/native/migraphx_c.dll"
$model = "$r2/inputs/yolox_nano.onnx"
$runs = @(
    @{ name='doctor'; args=@('--mode','doctor','--output',"$r2/results/doctor.json") },
    @{ name='photo'; args=@('--mode','detect','--model',$model,'--image',"$r2/inputs/astronaut.png",'--output',"$r2/results/photo.json") },
    @{ name='cache-parsed-miss'; args=@('--mode','cache','--model',$model,'--cache',"$CacheRoot/parsed",'--cache-kind','parsed','--output',"$r2/results/cache-parsed-miss.json") },
    @{ name='cache-parsed-hit-process2'; args=@('--mode','cache','--model',$model,'--cache',"$CacheRoot/parsed",'--cache-kind','parsed','--output',"$r2/results/cache-parsed-hit-process2.json") },
    @{ name='cache-parsed-hit-process3'; args=@('--mode','cache','--model',$model,'--cache',"$CacheRoot/parsed",'--cache-kind','parsed','--output',"$r2/results/cache-parsed-hit-process3.json") },
    @{ name='cache-compiled-miss'; args=@('--mode','cache','--model',$model,'--cache',"$CacheRoot/compiled",'--cache-kind','compiled','--output',"$r2/results/cache-compiled-miss.json") },
    @{ name='cache-compiled-hit-process2'; args=@('--mode','cache','--model',$model,'--cache',"$CacheRoot/compiled",'--cache-kind','compiled','--output',"$r2/results/cache-compiled-hit-process2.json") },
    @{ name='affine-trace'; args=@('--mode','trace','--output',"$r2/results/affine-trace.json") },
    @{ name='matmul-csharp'; args=@('--mode','verify','--model',"$article/examples/MigraphxCompute/matmul-relu.onnx",'--output',"$r2/results/matmul-csharp.json") }
)
$exits = [System.Collections.Generic.List[object]]::new()
foreach ($run in $runs) {
    Write-Host "Running $($run.name)"
    ('dotnet <examples>/MigraphxCompute/bin/Release/net10.0/MigraphxCompute.dll ' + (($run.args -join ' ').Replace($article,'<article>').Replace($CacheRoot,'<ASCII-cache>'))) | Add-Content "$r2/commands.txt"
    & dotnet $assembly @($run.args) *> "$r2/logs/$($run.name).log"
    $code = $LASTEXITCODE
    $exits.Add(@{ name=$run.name; exitCode=$code; date=(Get-Date).ToString('o') })
}
foreach ($case in @(@{name='affine-native'; model='affine-relu.onnx'; fast=0}, @{name='matmul-native'; model='matmul-relu.onnx'; fast=0}, @{name='matmul-native-fast'; model='matmul-relu.onnx'; fast=1})) {
    Write-Host "Running $($case.name)"
    & $Python "$article/examples/native-compile-probe.py" --native $native --model "$article/examples/MigraphxCompute/$($case.model)" --hip-root $root --fast-math $case.fast *> "$r2/logs/$($case.name).log"
    $exits.Add(@{ name=$case.name; exitCode=$LASTEXITCODE; date=(Get-Date).ToString('o') })
    "python <examples>/native-compile-probe.py --native <app>/runtimes/win-x64/native/migraphx_c.dll --model <examples>/MigraphxCompute/$($case.model) --hip-root <HIP_PATH> --fast-math $($case.fast)" | Add-Content "$r2/commands.txt"
}
$exits | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 "$r2/results/evidence-exits.json"
Write-Host 'Evidence runs complete; inspect failures and status before making claims.'
