[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('verify','trace')][string] $Mode,
    [Parameter(Mandatory)][string] $HipRoot,
    [string] $Architecture = 'gfx1100'
)
$ErrorActionPreference = 'Stop'
$articleRoot = Split-Path -Parent $PSScriptRoot
$evidenceRoot = Join-Path $PSScriptRoot "validation\round8\$Mode"
if (Test-Path -LiteralPath $evidenceRoot) { throw 'Use a new evidence directory; previous runs are not overwritten.' }
New-Item -ItemType Directory -Path $evidenceRoot | Out-Null
Set-Location -LiteralPath $articleRoot
$Host.UI.RawUI.WindowTitle = "ROCm C# - $Mode - actual PowerShell execution"
# Local console dimensions only; no saved terminal profile or system setting changes.
try {
    $size = $Host.UI.RawUI.WindowSize
    $size.Width = 130; $size.Height = 42
    $buffer = $Host.UI.RawUI.BufferSize
    $buffer.Width = [Math]::Max($buffer.Width, 130); $buffer.Height = [Math]::Max($buffer.Height, 1000)
    $Host.UI.RawUI.BufferSize = $buffer
    $Host.UI.RawUI.WindowSize = $size
} catch { Write-Warning "Console dimensions unchanged: $($_.Exception.Message)" }
$env:NUGET_PACKAGES = Join-Path (Split-Path -Parent $articleRoot) '.tools\round7-fresh-nuget'
$env:DOTNET_CLI_HOME = Join-Path (Split-Path -Parent $articleRoot) '.tools\round7-cli-home'
$env:NUGET_HTTP_CACHE_PATH = Join-Path (Split-Path -Parent $articleRoot) '.tools\round7-http-cache'
$PSStyle.OutputRendering = 'PlainText'
$started = (Get-Date).ToString('o')
Start-Transcript -LiteralPath (Join-Path $evidenceRoot 'transcript.txt') -NoClobber | Out-Null
$exitCode = 1
try {
    Write-Host "Actual PowerShell $($PSVersionTable.PSVersion) run | $started"
    Write-Host "Working directory: $articleRoot"
    $hardware = & (Join-Path $HipRoot 'bin\hipInfo.exe')
    if ($LASTEXITCODE -ne 0) { throw 'hipInfo failed.' }
    $hardware | Set-Content -LiteralPath (Join-Path $evidenceRoot 'hipInfo.txt') -Encoding utf8
    $hardware | Select-String '^Name:|^gcnArchName:' | ForEach-Object { Write-Host $_.Line }
    $result = "./research/validation/round8/$Mode/result.json"
    $arguments = @('-NoProfile', '-File', './examples/run-windows.ps1', '-HipRoot', $HipRoot,
                   '-Architecture', $Architecture, '-Mode', $Mode, '-OutputPath', $result)
    Write-Host ('Running: pwsh ' + ($arguments -join ' '))
    Write-Host ''
    & pwsh @arguments 2>&1 | Tee-Object -LiteralPath (Join-Path $evidenceRoot 'stdout-stderr.txt')
    $exitCode = $LASTEXITCODE
    Write-Host "Process exit code: $exitCode"
    if ($exitCode -ne 0) { throw "Example failed: exit=$exitCode" }
    Write-Host 'Execution finished; this console is kept open for an unedited window capture.'
} catch {
    Write-Error -ErrorRecord $_ -ErrorAction Continue
} finally {
    Stop-Transcript | Out-Null
    [ordered]@{
        started=$started; finished=(Get-Date).ToString('o'); mode=$Mode; exitCode=$exitCode
        processId=$PID; hostName=$Host.Name; powershell=$PSVersionTable.PSVersion.ToString()
        command=@('pwsh') + $arguments; cwd=$articleRoot
        runnerSha256=(Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
        logSha256=(Get-FileHash -LiteralPath (Join-Path $evidenceRoot 'stdout-stderr.txt') -Algorithm SHA256).Hash.ToLowerInvariant()
        transcriptSha256=(Get-FileHash -LiteralPath (Join-Path $evidenceRoot 'transcript.txt') -Algorithm SHA256).Hash.ToLowerInvariant()
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $evidenceRoot 'command.json') -Encoding utf8
}
