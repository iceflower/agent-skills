# Cross-platform Python script runner for Agent Skills (PowerShell)
# Usage: .\scripts\run.ps1 <path-to-script.py> [args...]

param(
    [Parameter(Position=0, Mandatory=$false)]
    [string]$ScriptPath,
    [Parameter(Position=1, ValueFromRemainingArguments=$true)]
    [string[]]$ScriptArgs
)

function Find-Python {
    foreach ($cmd in @("python3", "python")) {
        $pythonCmd = Get-Command $cmd -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            $version = & $cmd -c "import sys; print(sys.version_info.major)" 2>$null
            if ($version -eq "3") {
                return $cmd
            }
        }
    }
    return $null
}

function Show-InstallGuide {
    Write-Host ""
    Write-Host "ERROR: Python 3 is not installed." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Python 3 using one of the following methods:" -ForegroundColor Yellow
    Write-Host ""

    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        Write-Host "  Option 1 - winget (recommended):"
        Write-Host "    winget install Python.Python.3.12" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Option 2 - Chocolatey:"
        Write-Host "    choco install python3" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Option 3 - Scoop:"
        Write-Host "    scoop install python" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Option 4 - Microsoft Store:"
        Write-Host "    Search 'Python 3' in Microsoft Store" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  Option 5 - Manual download:"
        Write-Host "    https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  IMPORTANT: Check 'Add Python to PATH' during installation." -ForegroundColor Yellow
    }
    elseif ($IsMacOS) {
        Write-Host "  brew install python3" -ForegroundColor Cyan
    }
    elseif ($IsLinux) {
        Write-Host "  Use your distribution's package manager to install python3." -ForegroundColor Cyan
    }
    else {
        Write-Host "  Download from https://www.python.org/downloads/" -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host "After installation, restart your terminal and re-run this script."
    exit 1
}

if (-not $ScriptPath) {
    Write-Host "Usage: .\scripts\run.ps1 <path-to-script.py> [args...]"
    Write-Host ""
    Write-Host "Example:"
    Write-Host "  .\scripts\run.ps1 git-workflow\scripts\validate_commit_msg.py --help"
    exit 1
}

$python = Find-Python
if (-not $python) {
    Show-InstallGuide
}

if ($ScriptArgs) {
    & $python $ScriptPath @ScriptArgs
} else {
    & $python $ScriptPath
}

exit $LASTEXITCODE
