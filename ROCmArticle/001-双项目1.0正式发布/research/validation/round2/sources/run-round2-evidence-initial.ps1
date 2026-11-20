[CmdletBinding()]
param([Parameter(Mandatory)][string] $HipRoot, [string] $Python = 'python')
$ErrorActionPreference = 'Stop'
$article = Split-Path -Parent $PSScriptRoot
$r2 = Join-Path $PSScriptRoot 'validation/round2'
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
    @{ name='cache-miss'; args=@('--mode','cache','--model',$model,'--cache',"$article/.validation/round2-model-cache",'--output',"$r2/results/cache-miss.json") },
    @{ name='cache-hit-process2'; args=@('--mode','cache','--model',$model,'--cache',"$article/.validation/round2-model-cache",'--output',"$r2/results/cache-hit-process2.json") },
    @{ name='cache-hit-process3'; args=@('--mode','cache','--model',$model,'--cache',"$article/.validation/round2-model-cache",'--output',"$r2/results/cache-hit-process3.json") },
    @{ name='affine-trace'; args=@('--mode','trace','--output',"$r2/results/affine-trace.json") },
    @{ name='matmul-csharp'; args=@('--mode','verify','--model',"$article/examples/MigraphxCompute/matmul-relu.onnx",'--output',"$r2/results/matmul-csharp.json") }
)
$exits = [System.Collections.Generic.List[object]]::new()
foreach ($run in $runs) {
    Write-Host "Running $($run.name)"
    ('dotnet <examples>/MigraphxCompute/bin/Release/net10.0/MigraphxCompute.dll ' + (($run.args -join ' ').Replace($article,'<article>'))) | Add-Content "$r2/commands.txt"
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
