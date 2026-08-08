[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [switch]$BackendOnly,
    [switch]$FrontendOnly,
    [switch]$NoBrowser,
    [ValidateRange(1, 65535)]
    [int]$BackendPort = 8000,
    [ValidateRange(1, 65535)]
    [int]$FrontendPort = 5173
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$ProjectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$BackendRoot = Join-Path $ProjectRoot 'backend'
$FrontendRoot = Join-Path $ProjectRoot 'frontend'
$BackendVenv = Join-Path $BackendRoot '.venv'
$BackendPython = Join-Path $BackendVenv 'Scripts\python.exe'
$BackendEnv = Join-Path $BackendRoot '.env'
$FrontendEnv = Join-Path $FrontendRoot '.env'

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-WarningMessage {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "[ OK ] $Message" -ForegroundColor Green
}

function Throw-SetupError {
    param(
        [string]$Message,
        [string[]]$Hints = @()
    )

    $errorMessage = $Message
    if ($Hints.Count -gt 0) {
        $errorMessage += "`n`n建議：`n- " + ($Hints -join "`n- ")
    }
    throw $errorMessage
}

function Get-CommandPath {
    param(
        [Parameter(Mandatory)]
        [string]$Name,
        [string]$InstallHint
    )

    $command = Get-Command $Name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $command) {
        Throw-SetupError "找不到 $Name。" @($InstallHint)
    }
    return $command.Source
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,
        [string[]]$Arguments = @(),
        [Parameter(Mandatory)]
        [string]$WorkingDirectory,
        [Parameter(Mandatory)]
        [string]$FailureMessage
    )

    Push-Location $WorkingDirectory
    try {
        & $FilePath @Arguments
        $exitCode = $LASTEXITCODE
    }
    catch {
        throw "$FailureMessage`n$($_.Exception.Message)"
    }
    finally {
        Pop-Location
    }

    if ($exitCode -ne 0) {
        throw "$FailureMessage (exit code: $exitCode)"
    }
}

function Get-ListeningPortOwners {
    param([int]$Port)

    try {
        $connections = @(Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction Stop)
    }
    catch {
        return @()
    }

    $owners = @()
    foreach ($connection in $connections) {
        $ownerId = $connection.OwningProcess
        try {
            $processName = (Get-Process -Id $ownerId -ErrorAction Stop).ProcessName
        }
        catch {
            $processName = '未知程序'
        }
        $owners += "PID $ownerId ($processName)"
    }
    return @($owners | Select-Object -Unique)
}

function Test-ListeningPort {
    param([int]$Port)
    return @(Get-ListeningPortOwners -Port $Port).Count -gt 0
}

function Test-HttpReady {
    param([string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-ForBackend {
    param([int]$Port)

    for ($attempt = 1; $attempt -le 15; $attempt++) {
        if (Test-HttpReady -Url "http://127.0.0.1:$Port/health") {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Wait-ForPort {
    param([int]$Port)

    for ($attempt = 1; $attempt -le 15; $attempt++) {
        if (Test-ListeningPort -Port $Port) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

function Get-PowerShellPath {
    $pwsh = Get-Command 'pwsh.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $pwsh) {
        return $pwsh.Source
    }

    $powershell = Get-Command 'powershell.exe' -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $powershell) {
        Throw-SetupError '找不到 PowerShell，無法開啟前後端視窗。' @('記得用 Windows PowerShell 或 PowerShell 7 執行腳本。')
    }
    return $powershell.Source
}

function ConvertTo-PowerShellLiteral {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Get-DatabaseMode {
    if (-not (Test-Path -LiteralPath $BackendEnv)) {
        return 'disabled'
    }

    $databaseLine = Get-Content -LiteralPath $BackendEnv -ErrorAction Stop | Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } | Select-Object -First 1

    if ($null -eq $databaseLine) {
        return 'disabled'
    }

    $databaseUrl = ($databaseLine -replace '^\s*DATABASE_URL\s*=\s*', '').Trim()
    if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
        return 'disabled'
    }

    if ($databaseUrl -match '<password>|<project-ref>|請替換') {
        return 'placeholder'
    }
    return 'configured'
}

function Ensure-Backend {
    param([string]$PythonPath)

    if (-not (Test-Path -LiteralPath $BackendRoot)) {
        Throw-SetupError '找不到 backend 資料夾。' @('請從專案根目錄執行 .\start.ps1。')
    }

    if (-not (Test-Path -LiteralPath $BackendPython)) {
        if ($SkipInstall) {
            Throw-SetupError 'backend/.venv 尚未建立，且目前使用了 -SkipInstall。' @('移除 -SkipInstall，讓腳本自動建立虛擬環境。')
        }
        Write-Info '建立 Python 虛擬環境。'
        Invoke-CheckedCommand $PythonPath @('-m', 'venv', $BackendVenv) $ProjectRoot '建立 Python 虛擬環境失敗。'
    }

    if (-not $SkipInstall) {
        Write-Info '檢查後端 Python 依賴。'
        $sitePackages = Join-Path $BackendVenv 'Lib\site-packages'
        $requiredPackages = @('fastapi', 'uvicorn', 'asyncpg', 'pydantic_settings')
        $dependenciesReady = @($requiredPackages | Where-Object { Test-Path -LiteralPath (Join-Path $sitePackages $_) }).Count -eq $requiredPackages.Count
        if (-not $dependenciesReady) {
            Write-Info '安裝後端 Python 依賴。'
            Invoke-CheckedCommand $BackendPython @('-m', 'pip', 'install', '-r', 'requirements.txt') $BackendRoot '安裝後端依賴失敗。' 
        }
    }
    elseif (-not (Test-Path -LiteralPath (Join-Path $BackendVenv 'Lib\site-packages\fastapi'))) {
        Throw-SetupError '後端依賴尚未安裝，且目前使用了 -SkipInstall。' @('移除 -SkipInstall，讓腳本自動執行 pip install。')
    }

    if (-not (Test-Path -LiteralPath $BackendEnv)) {
        Copy-Item -LiteralPath (Join-Path $BackendRoot '.env.example') -Destination $BackendEnv
        Write-WarningMessage '已建立 backend/.env；目前 DATABASE_URL 是範例值，後端會以無資料庫模式啟動。'
    }
    Write-Success '後端環境準備完成。'
}

function Ensure-Frontend {
    if (-not (Test-Path -LiteralPath $FrontendRoot)) {
        Throw-SetupError '找不到 frontend 資料夾。' @('請從專案根目錄執行 .\start.ps1。')
    }

    if (-not (Test-Path -LiteralPath (Join-Path $FrontendRoot 'package.json'))) {
        Throw-SetupError '找不到 frontend/package.json。' @('請確認專案檔案是否完整。')
    }

    $nodeModules = Join-Path $FrontendRoot 'node_modules'
    if (-not (Test-Path -LiteralPath $nodeModules)) {
        if ($SkipInstall) {
            Throw-SetupError 'frontend/node_modules 尚未建立，且目前使用了 -SkipInstall。' @('移除 -SkipInstall，讓腳本自動執行 npm install。')
        }
        Write-Info '安裝前端 npm 依賴。'
        $npmArguments = @('install')
        Invoke-CheckedCommand $script:NpmPath $npmArguments $FrontendRoot '安裝前端依賴失敗。' 
    }
    elseif (-not (Test-Path -LiteralPath (Join-Path $nodeModules 'vite'))) {
        if ($SkipInstall) {
            Throw-SetupError 'frontend/node_modules 不完整，且目前使用了 -SkipInstall。' @('移除 -SkipInstall，讓腳本自動補齊 npm 依賴。')
        }
        Write-Info '前端依賴不完整，重新執行 npm install。'
        Invoke-CheckedCommand $script:NpmPath @('install') $FrontendRoot '補齊前端依賴失敗。'
    }

    if (-not (Test-Path -LiteralPath $FrontendEnv)) {
        Copy-Item -LiteralPath (Join-Path $FrontendRoot '.env.example') -Destination $FrontendEnv
        Write-Info '已建立 frontend/.env。'
    }
    Write-Success '前端環境準備完成。'
}

function Assert-PortOrReuse {
    param(
        [int]$Port,
        [string]$ServiceName,
        [string]$HealthUrl
    )

    if (-not (Test-ListeningPort -Port $Port)) {
        return $false
    }

    if ($HealthUrl -and (Test-HttpReady -Url $HealthUrl)) {
        Write-WarningMessage "$ServiceName 已在 port $Port 執行，將沿用現有服務。"
        return $true
    }

    $owners = @(Get-ListeningPortOwners -Port $Port)
    $ownerText = if ($owners.Count -gt 0) { $owners -join ', ' } else { '無法取得程序資訊' }
    Throw-SetupError "$ServiceName 需要的 port $Port 已被占用（$ownerText）。" @(
        "關閉占用該 port 的程序後重試。",
        "或使用參數調整 port，例如 .\start.ps1 -FrontendPort 5174。"
    )
}

function Start-BackendWindow {
    param(
        [string]$PowerShellPath,
        [string]$PythonPath,
        [bool]$DisableDatabase
    )

    $backendLiteral = ConvertTo-PowerShellLiteral $BackendRoot
    $pythonLiteral = ConvertTo-PowerShellLiteral $PythonPath
    $corsOrigins = ConvertTo-PowerShellLiteral "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"
    $databaseOverride = if ($DisableDatabase) { "`$env:DATABASE_URL = ''" } else { '' }
    $windowTitle = ConvertTo-PowerShellLiteral '活米村後端 FastAPI'

    $childCommand = @"
`$ErrorActionPreference = 'Continue'
`$Host.UI.RawUI.WindowTitle = $windowTitle
Set-Location -LiteralPath $backendLiteral
`$env:CORS_ORIGINS = $corsOrigins
$databaseOverride
Write-Host '[INFO] 啟動 FastAPI，停止請按 Ctrl+C。' -ForegroundColor Cyan
try {
    & $pythonLiteral -m uvicorn app.main:app --host 0.0.0.0 --port $BackendPort --reload
    `$exitCode = `$LASTEXITCODE
    if (`$exitCode -ne 0) {
        throw "FastAPI 結束，exit code: `$exitCode"
    }
}
catch {
    Write-Host '[ERROR] 後端啟動失敗。' -ForegroundColor Red
    Write-Host `$_.Exception.Message -ForegroundColor Red
    Write-Host '請確認 backend/.env 的 DATABASE_URL；若只想查看介面，可暫時移除 DATABASE_URL。' -ForegroundColor Yellow
    Read-Host '按 Enter 關閉此視窗'
}
"@

    return Start-Process -FilePath $PowerShellPath -WorkingDirectory $BackendRoot -PassThru -ArgumentList @(
        '-NoLogo',
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-NoExit',
        '-Command',
        $childCommand
    )
}

function Start-FrontendWindow {
    param(
        [string]$PowerShellPath,
        [string]$NpmPath
    )

    $frontendLiteral = ConvertTo-PowerShellLiteral $FrontendRoot
    $npmLiteral = ConvertTo-PowerShellLiteral $NpmPath
    $windowTitle = ConvertTo-PowerShellLiteral '活米村前端 Vite'

    $childCommand = @"
`$ErrorActionPreference = 'Continue'
`$Host.UI.RawUI.WindowTitle = $windowTitle
Set-Location -LiteralPath $frontendLiteral
Write-Host '[INFO] 啟動 Vite，停止請按 Ctrl+C。' -ForegroundColor Cyan
try {
    & $npmLiteral run dev -- --host 127.0.0.1 --port $FrontendPort
    `$exitCode = `$LASTEXITCODE
    if (`$exitCode -ne 0) {
        throw "Vite 結束，exit code: `$exitCode"
    }
}
catch {
    Write-Host '[ERROR] 前端啟動失敗。' -ForegroundColor Red
    Write-Host `$_.Exception.Message -ForegroundColor Red
    Write-Host '請確認 Node.js 版本與 frontend/node_modules 是否完整。' -ForegroundColor Yellow
    Read-Host '按 Enter 關閉此視窗'
}
"@

    return Start-Process -FilePath $PowerShellPath -WorkingDirectory $FrontendRoot -PassThru -ArgumentList @(
        '-NoLogo',
        '-NoProfile',
        '-ExecutionPolicy',
        'Bypass',
        '-NoExit',
        '-Command',
        $childCommand
    )
}

try {
    if ($BackendOnly -and $FrontendOnly) {
        Throw-SetupError '不能同時使用 -BackendOnly 與 -FrontendOnly。'
    }

    $startBackend = -not $FrontendOnly
    $startFrontend = -not $BackendOnly

    Write-Host '活米村網站啟動器' -ForegroundColor Magenta
    Write-Host "專案：$ProjectRoot" -ForegroundColor DarkGray

    $powerShellPath = Get-PowerShellPath

    $pythonPath = $null
    $script:NpmPath = $null
    if ($startBackend) {
        $pythonPath = Get-CommandPath 'python.exe' '請安裝 Python 3.11 或更新版本，並將它加入 PATH。'
    }
    if ($startFrontend) {
        $script:NpmPath = Get-CommandPath 'npm.cmd' '請安裝 Node.js 22.18+，並將它加入 PATH。'
        $nodePath = Get-CommandPath 'node.exe' '請安裝 Node.js 22.18+，並將它加入 PATH。'

        $nodeVersion = (& $nodePath --version 2>$null).Trim()
        if ($nodeVersion -notmatch '^v(?<major>\d+)\.(?<minor>\d+)\.(?<patch>\d+)') {
            Throw-SetupError "無法辨識 Node.js 版本：$nodeVersion。" @('請重新安裝 Node.js 22.18 或更新版本。')
        }
        $nodeMajor = [int]$Matches.major
        $nodeMinor = [int]$Matches.minor
        if (($nodeMajor -lt 22) -or (($nodeMajor -eq 22) -and ($nodeMinor -lt 18))) {
            Throw-SetupError "目前 Node.js 是 $nodeVersion，不符合 package.json 宣告的 22.18+。" @(
                '更新 Node.js 至 22.18 或更新版本後再執行。',
                '更新後可用 node --version 確認版本。'
            )
        }
        else {
            Write-Success "Node.js $nodeVersion"
        }
    }

    if ($startBackend) {
        Ensure-Backend -PythonPath $pythonPath
    }
    if ($startFrontend) {
        Ensure-Frontend
    }

    $backendReused = $false
    $frontendReused = $false
    if ($startBackend) {
        $backendReused = Assert-PortOrReuse -Port $BackendPort -ServiceName '後端' -HealthUrl "http://127.0.0.1:$BackendPort/health"
    }
    if ($startFrontend) {
        $frontendReused = Assert-PortOrReuse -Port $FrontendPort -ServiceName '前端' -HealthUrl "http://127.0.0.1:$FrontendPort/"
    }

    $backendProcess = $null
    $frontendProcess = $null
    if ($startBackend -and -not $backendReused) {
        $databaseMode = Get-DatabaseMode
        $disableDatabase = $databaseMode -ne 'configured'
        if ($databaseMode -eq 'placeholder') {
            Write-WarningMessage 'backend/.env 仍是範例 DATABASE_URL；先以無資料庫模式啟動，介面可以查看，但登入與遊戲操作不可用。'
        }
        elseif ($databaseMode -eq 'disabled') {
            Write-WarningMessage 'backend/.env 沒有有效 DATABASE_URL；先以無資料庫模式啟動。'
        }
        $backendProcess = Start-BackendWindow -PowerShellPath $powerShellPath -PythonPath $BackendPython -DisableDatabase $disableDatabase
    }

    if ($startBackend -and -not $backendReused) {
        if (Wait-ForBackend -Port $BackendPort) {
            Write-Success "後端已啟動：http://localhost:$BackendPort"
        }
        else {
            Write-WarningMessage "後端尚未回應：http://localhost:$BackendPort/health；請查看新開的後端視窗。"
        }
    }

    if ($startFrontend -and -not $frontendReused) {
        $frontendProcess = Start-FrontendWindow -PowerShellPath $powerShellPath -NpmPath $script:NpmPath
    }

    if ($startFrontend) {
        if ($frontendReused -or (Wait-ForPort -Port $FrontendPort)) {
            Write-Success "前端已啟動：http://localhost:$FrontendPort"
            if (-not $NoBrowser) {
                Start-Process "http://localhost:$FrontendPort"
            }
        }
        else {
            Write-WarningMessage "前端尚未監聽 port $FrontendPort；請查看新開的前端視窗。"
        }
    }

    Write-Host ''
    Write-Host '啟動程序已完成。關閉網站：分別在前後端視窗按 Ctrl+C。' -ForegroundColor Green
}
catch {
    Write-Host ''
    Write-Host '[ERROR] 網站啟動失敗。' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ''
    Write-Host '若是 PowerShell 權限錯誤，請用以下方式執行：' -ForegroundColor Yellow
    Write-Host 'powershell -ExecutionPolicy Bypass -File .\start.ps1' -ForegroundColor Yellow
    exit 1
}
