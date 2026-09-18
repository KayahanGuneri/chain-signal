param([switch]$RunSmoke, [switch]$HoldForBrowser)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$taskProject = 'chainsignal-phase2-' + [guid]::NewGuid().ToString('N').Substring(0, 12)
$taskVariables = @{
    POSTGRES_DB = 'phase2'; POSTGRES_USER = 'phase2'; POSTGRES_PASSWORD = [guid]::NewGuid().ToString('N')
    POSTGRES_PORT = '0'; BACKEND_PORT = '0'; FRONTEND_PORT = '0'
    COMPOSE_BAKE = 'false'
}
$taskPrevious = @{}
$taskPorts = @{}
try {
    Push-Location $taskRoot
    foreach ($taskKey in $taskVariables.Keys) {
        $taskPrevious[$taskKey] = [Environment]::GetEnvironmentVariable($taskKey)
        [Environment]::SetEnvironmentVariable($taskKey, $taskVariables[$taskKey])
    }
    docker compose -p $taskProject config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'Compose config failed' }
    docker compose -p $taskProject up --detach --build --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) { throw 'Disposable Compose build/startup failed' }
    foreach ($taskService in @('postgres', 'backend', 'frontend')) {
        $taskIdOutput = docker compose -p $taskProject ps -q $taskService
        if ($LASTEXITCODE -ne 0) { throw 'Compose metadata lookup failed' }
        $taskInspectOutput = docker inspect ($taskIdOutput -join '').Trim()
        if ($LASTEXITCODE -ne 0) { throw 'Docker inspect failed' }
        $taskInspect = ($taskInspectOutput -join "`n" | ConvertFrom-Json)[0]
        $taskContainerPort = switch ($taskService) {
            'postgres' { '5432/tcp' }
            'backend' { '8080/tcp' }
            'frontend' { '3000/tcp' }
        }
        $taskPort = $taskInspect.NetworkSettings.Ports.$taskContainerPort[0].HostPort
        $taskPorts[$taskService] = $taskPort
        if ($taskService -eq 'postgres') { continue }
        $taskPath = if ($taskService -eq 'backend') { '/actuator/health' } else { '/api/events' }
        $taskResponse = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$taskPort$taskPath" -TimeoutSec 20
        if ($taskResponse.StatusCode -ne 200) { throw "Container HTTP check failed: $taskService" }
        Write-Output "PASS: $taskService container healthy and HTTP 200"
    }
    docker compose -p $taskProject exec -T postgres psql -U phase2 -d phase2 -c 'SELECT version, success FROM flyway_schema_history ORDER BY installed_rank; SELECT postgis_version();'
    if ($LASTEXITCODE -ne 0) { throw 'Container Flyway/PostGIS check failed' }
    docker compose -p $taskProject ps
    if ($LASTEXITCODE -ne 0) { throw 'Compose status check failed' }
    $taskBackendUrl = "http://127.0.0.1:$($taskPorts.backend)"
    $taskFrontendUrl = "http://127.0.0.1:$($taskPorts.frontend)"
    if ($RunSmoke) {
        $taskDatabaseVariables = @{
            CHAIN_SIGNAL_DB_HOST = '127.0.0.1'; CHAIN_SIGNAL_DB_PORT = $taskPorts.postgres
            CHAIN_SIGNAL_DB_NAME = 'phase2'; CHAIN_SIGNAL_DB_USER = 'phase2'
            CHAIN_SIGNAL_DB_PASSWORD = $taskVariables.POSTGRES_PASSWORD
        }
        foreach ($taskKey in $taskDatabaseVariables.Keys) {
            $taskPrevious[$taskKey] = [Environment]::GetEnvironmentVariable($taskKey)
            [Environment]::SetEnvironmentVariable($taskKey, $taskDatabaseVariables[$taskKey])
        }
        $taskOutput = Join-Path $taskRoot '.smoke'
        New-Item -ItemType Directory -Force $taskOutput | Out-Null
        & (Join-Path $taskRoot 'data-pipeline/.venv/Scripts/python.exe') scripts/phase2_smoke.py --backend $taskBackendUrl --frontend $taskFrontendUrl --output $taskOutput
        if ($LASTEXITCODE -ne 0) { throw 'Full Compose integration smoke failed' }
    }
    if ($HoldForBrowser) {
        # Explicitly disposable demo assets make the real dashboard workflow visible.
        foreach ($taskType in @('PORT', 'SUPPLIER')) {
            $taskBody = @{
                type = $taskType; name = "Demo $($taskType.ToLowerInvariant())"; country = 'Türkiye'; city = 'Istanbul'
                latitude = $(if ($taskType -eq 'PORT') { 41.0 } else { 41.005 })
                longitude = 29.0; criticality = 4
            } | ConvertTo-Json
            Invoke-RestMethod -Method Post -Uri "$taskBackendUrl/api/supply-assets" -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($taskBody)) | Out-Null
        }
        $taskDone = Join-Path $taskRoot '.smoke/compose-browser-check.done'
        if (Test-Path -LiteralPath $taskDone) { Remove-Item -LiteralPath $taskDone }
        Write-Output "Browser verification URL: $taskFrontendUrl"
        Write-Output "Disposable backend URL: $taskBackendUrl"
        for ($taskTry = 0; $taskTry -lt 300; $taskTry++) {
            if (Test-Path -LiteralPath $taskDone) { break }
            Start-Sleep -Seconds 1
        }
    }
} finally {
    # This unique project owns its disposable volume; existing Compose data is untouched.
    docker compose -p $taskProject down --volumes --remove-orphans
    foreach ($taskKey in $taskPrevious.Keys) { [Environment]::SetEnvironmentVariable($taskKey, $taskPrevious[$taskKey]) }
    Pop-Location
}
