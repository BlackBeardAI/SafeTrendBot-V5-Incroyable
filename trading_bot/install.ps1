#Requires -Version 5.1
<#
.SYNOPSIS
    Installateur PowerShell moderne pour SafeTrendBot V5
.DESCRIPTION
    Installe Python, les dépendances, et configure SafeTrendBot sur Windows
.EXAMPLE
    .\install.ps1
#>

param(
    [switch]$Headless,
    [switch]$SkipML,
    [switch]$SkipWeb,
    [string]$InstallPath = "$env:LOCALAPPDATA\SafeTrendBot"
)

$ErrorActionPreference = "Stop"

function Write-Header($text) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Test-Python {
    try {
        $ver = python --version 2>&1
        if ($ver -match "Python 3\.(\d+)") {
            if ([int]$matches[1] -lt 10) {
                Write-Error "Python 3.10+ requis. Version actuelle: $ver"
            }
            Write-Host "✅ $ver" -ForegroundColor Green
            return $true
        }
    } catch {
        Write-Error "Python non trouvé. Installez Python 3.10+ depuis python.org"
    }
}

function Install-Deps {
    Write-Header "Installation des dépendances"
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if (-not $?) {
        Write-Warning "Installation standard échouée, fallback minimal..."
        python -m pip install PyQt6 numpy pandas yfinance requests reportlab
    }
}

function Install-Optional {
    if (-not $SkipML) {
        Write-Header "Dépendances ML (optionnel)"
        $reply = Read-Host "Installer scikit-learn + hmmlearn ? [y/N]"
        if ($reply -eq 'y') {
            python -m pip install scikit-learn hmmlearn
        }
    }
    if (-not $SkipWeb) {
        Write-Header "Dépendances Web (optionnel)"
        $reply = Read-Host "Installer fastapi + uvicorn ? [y/N]"
        if ($reply -eq 'y') {
            python -m pip install fastapi uvicorn websockets
        }
    }
}

function New-Shortcut {
    try {
        $WshShell = New-Object -ComObject WScript.Shell
        $shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\SafeTrendBot V5.lnk")
        $shortcut.TargetPath = "python"
        $shortcut.Arguments = "$(Get-Location)\main.py"
        $shortcut.WorkingDirectory = (Get-Location)
        $shortcut.IconLocation = "python.exe"
        $shortcut.Save()
        Write-Host "✅ Raccourci bureau créé" -ForegroundColor Green
    } catch {
        Write-Warning "Impossible de créer le raccourci"
    }
}

function Register-TaskScheduler {
    Write-Header "Tâche planifiée (optionnel)"
    $reply = Read-Host "Créer une tâche planifiée pour démarrage auto ? [y/N]"
    if ($reply -ne 'y') { return }
    
    $action = New-ScheduledTaskAction -Execute "python" -Argument "$(Get-Location)\headless.py --paper" -WorkingDirectory (Get-Location)
    $trigger = New-ScheduledTaskTrigger -AtLogon
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries
    Register-ScheduledTask -TaskName "SafeTrendBotV5" -Action $action -Trigger $trigger -Settings $settings -Force
    Write-Host "✅ Tâche 'SafeTrendBotV5' créée" -ForegroundColor Green
}

# MAIN
Write-Header "SafeTrendBot V5 — Installateur Windows"
Write-Host "OS: $([System.Environment]::OSVersion.VersionString)"

if (-not (Test-Python)) { exit 1 }

# Créer le répertoire d'installation
New-Item -ItemType Directory -Force -Path $InstallPath | Out-Null
Write-Host "📁 Installé dans: $InstallPath" -ForegroundColor Gray

Install-Deps
Install-Optional
New-Shortcut
Register-TaskScheduler

Write-Header "Installation terminée"
Write-Host @"
Lancer SafeTrendBot:
  → UI Desktop : python main.py
  → Headless   : python headless.py --paper
  → Web Dash   : http://localhost:8080

Documentation: README.md
"@ -ForegroundColor Green
