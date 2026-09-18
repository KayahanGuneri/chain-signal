param([switch]$RunTests, [switch]$SkipLiveSource, [switch]$HoldForBrowser)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskOutput = Join-Path $taskRoot '.smoke'
New-Item -ItemType Directory -Force $taskOutput | Out-Null
$taskContainer = 'chainsignal-phase2-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
$taskPassword = [guid]::NewGuid().ToString('N')
$taskJava = Join-Path $env:JAVA_HOME 'bin/java.exe'
$taskPython = Join-Path $taskRoot 'data-pipeline/.venv/Scripts/python.exe'
$taskBackend = $null
$taskFrontend = $null
$taskEnvironment = @{}
function Set-TaskEnvironment([string]$Name, [string]$Value) {
    if (!$taskEnvironment.ContainsKey($Name)) { $taskEnvironment[$Name] = [Environment]::GetEnvironmentVariable($Name) }
    [Environment]::SetEnvironmentVariable($Name, $Value)
}
function Get-FreePort {
    $taskListener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
    $taskListener.Start()
    $taskPort = $taskListener.LocalEndpoint.Port
    $taskListener.Stop()
    return $taskPort
}
function Wait-Http([string]$Url, $Process) {
    for ($taskTry = 0; $taskTry -lt 90; $taskTry++) {
        if ($Process.HasExited) { throw "Service exited before becoming healthy: $Url; inspect .smoke logs" }
        try { $taskResponse = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2; if ($taskResponse.StatusCode -eq 200) { return } } catch { }
        Start-Sleep -Seconds 1
    }
    throw "Service did not become healthy: $Url"
}
try {
    Push-Location $taskRoot
    docker run --detach --name $taskContainer --publish 127.0.0.1::5432 --env POSTGRES_DB=phase2 --env POSTGRES_USER=phase2 --env "POSTGRES_PASSWORD=$taskPassword" postgis/postgis:16-3.5 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Disposable PostGIS startup failed' }
    $taskInspectOutput = docker inspect $taskContainer
    if ($LASTEXITCODE -ne 0) { throw 'Docker inspect failed' }
    $taskInspect = ($taskInspectOutput -join "`n" | ConvertFrom-Json)[0]
    $taskDbPort = $taskInspect.NetworkSettings.Ports.'5432/tcp'[0].HostPort
    for ($taskTry = 0; $taskTry -lt 60; $taskTry++) {
        docker exec $taskContainer pg_isready -U phase2 -d phase2 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { break }
        Start-Sleep -Seconds 1
    }
    if ($LASTEXITCODE -ne 0) { throw 'PostGIS readiness failed' }
    $taskBackendPort = Get-FreePort
    $taskFrontendPort = Get-FreePort
    Set-TaskEnvironment DB_HOST '127.0.0.1'
    Set-TaskEnvironment DB_PORT $taskDbPort
    Set-TaskEnvironment POSTGRES_DB 'phase2'
    Set-TaskEnvironment POSTGRES_USER 'phase2'
    Set-TaskEnvironment POSTGRES_PASSWORD $taskPassword
    Set-TaskEnvironment SPRING_DATASOURCE_URL "jdbc:postgresql://127.0.0.1:$taskDbPort/phase2"
    Set-TaskEnvironment SPRING_DATASOURCE_USERNAME 'phase2'
    Set-TaskEnvironment SPRING_DATASOURCE_PASSWORD $taskPassword
    Set-TaskEnvironment SERVER_PORT ([string]$taskBackendPort)
    Set-TaskEnvironment CHAIN_SIGNAL_DB_HOST '127.0.0.1'
    Set-TaskEnvironment CHAIN_SIGNAL_DB_PORT $taskDbPort
    Set-TaskEnvironment CHAIN_SIGNAL_DB_NAME 'phase2'
    Set-TaskEnvironment CHAIN_SIGNAL_DB_USER 'phase2'
    Set-TaskEnvironment CHAIN_SIGNAL_DB_PASSWORD $taskPassword
    Set-TaskEnvironment CHAIN_SIGNAL_TEST_DATABASE '1'
    Set-TaskEnvironment BACKEND_URL "http://127.0.0.1:$taskBackendPort"
    Set-TaskEnvironment NEXT_TELEMETRY_DISABLED '1'
    $taskJar = Join-Path $taskRoot 'backend/target/chainsignal-backend-0.1.0-SNAPSHOT.jar'
    if (!(Test-Path -LiteralPath $taskJar)) { throw 'Build backend with mvn package first' }
    $taskBackend = Start-Process -FilePath $taskJava -ArgumentList @('-jar', ('"' + $taskJar + '"')) -WorkingDirectory $taskRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskOutput 'backend.log') -RedirectStandardError (Join-Path $taskOutput 'backend-error.log') -PassThru
    Wait-Http "$env:BACKEND_URL/actuator/health" $taskBackend
    $taskNode = (Get-Command node.exe).Source
    $taskFrontend = Start-Process -FilePath $taskNode -ArgumentList @('node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', $taskFrontendPort) -WorkingDirectory (Join-Path $taskRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskOutput 'frontend.log') -RedirectStandardError (Join-Path $taskOutput 'frontend-error.log') -PassThru
    Wait-Http "http://127.0.0.1:$taskFrontendPort" $taskFrontend
    $taskArguments = @('scripts/phase2_smoke.py', '--backend', $env:BACKEND_URL, '--frontend', "http://127.0.0.1:$taskFrontendPort", '--output', $taskOutput)
    if ($SkipLiveSource) { $taskArguments += '--skip-live-source' }
    & $taskPython @taskArguments
    if ($LASTEXITCODE -ne 0) { throw 'Integration smoke failed' }
    if ($RunTests) {
        Push-Location (Join-Path $taskRoot 'data-pipeline')
        try {
            # Keep Parquet fixture paths below Windows native path limits and avoid
            # reusing pytest directories created under another Windows identity.
            $taskTestTemp = Join-Path ([IO.Path]::GetTempPath()) ('cs-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
            if (Test-Path -LiteralPath $taskTestTemp) { throw 'Expected a fresh pytest temporary directory' }
            Write-Output "Python acceptance: $taskPython -m pytest -q --basetemp $taskTestTemp -o cache_dir=$taskTestTemp-cache"
            & $taskPython -m pytest -q --basetemp $taskTestTemp -o "cache_dir=$taskTestTemp-cache"
            if ($LASTEXITCODE -ne 0) { throw 'Python tests failed' }
        } finally { Pop-Location }
    }
    if ($HoldForBrowser) {
        $taskDone = Join-Path $taskOutput 'browser-check.done'
        if (Test-Path -LiteralPath $taskDone) { Remove-Item -LiteralPath $taskDone }
        Write-Output "Browser verification URL: http://127.0.0.1:$taskFrontendPort"
        Write-Output "Disposable backend URL: $env:BACKEND_URL"
        # A bounded hold allows UI verification while preserving cleanup on timeout.
        for ($taskTry = 0; $taskTry -lt 300; $taskTry++) {
            if (Test-Path -LiteralPath $taskDone) { break }
            Start-Sleep -Seconds 1
        }
    }
} finally {
    if ($taskFrontend -and !$taskFrontend.HasExited) { Stop-Process -Id $taskFrontend.Id -Force }
    if ($taskBackend -and !$taskBackend.HasExited) { Stop-Process -Id $taskBackend.Id -Force }
    docker rm --force $taskContainer 2>&1 | Out-Null
    foreach ($taskName in $taskEnvironment.Keys) { [Environment]::SetEnvironmentVariable($taskName, $taskEnvironment[$taskName]) }
    Pop-Location
}
