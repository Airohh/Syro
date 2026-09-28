#Requires -Version 5.1
<#
.SYNOPSIS
  Démarre Syro sous Windows (équivalent de `make up` + `make demo`).
.EXAMPLE
  .\start-syro.ps1          # démarre la stack et ouvre le navigateur
  .\start-syro.ps1 -Demo    # + charge les documents de démo
#>
param(
  [switch]$Demo,
  [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

Write-Host ">> docker compose up -d --build" -ForegroundColor Cyan
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose a échoué (Docker Desktop est-il lancé ?)" }

Write-Host ">> Attente de l'API (1er démarrage : téléchargement des modèles, quelques minutes)..." -ForegroundColor Cyan
$deadline = (Get-Date).AddMinutes(20)
do {
  Start-Sleep -Seconds 5
  try { $ok = (Invoke-WebRequest -UseBasicParsing http://localhost:8000/health).StatusCode -eq 200 } catch { $ok = $false }
} until ($ok -or (Get-Date) -gt $deadline)
if (-not $ok) { throw "L'API ne répond pas : docker compose logs syro-api" }
Write-Host "OK API prête" -ForegroundColor Green

if ($Demo) {
  Write-Host ">> Chargement des documents de démo" -ForegroundColor Cyan
  docker compose exec syro-api python scripts/load_demo.py
}

Write-Host ""
Write-Host "UI  : http://localhost:5173   (demo@syro.local / syro-demo)"
Write-Host "API : http://localhost:8000/docs"
if (-not $NoBrowser) { Start-Process "http://localhost:5173" }
