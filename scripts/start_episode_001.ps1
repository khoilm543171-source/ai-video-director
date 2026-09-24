$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$EpisodeId = "episode_001_fuel_oil_purifier"
$EpisodeDir = Join-Path $RepoRoot "outputs\episodes\$EpisodeId"

Write-Host ""
Write-Host "=== Tiny Engine Cadet - Episode 001 ===" -ForegroundColor Cyan
Write-Host "Fuel Oil Purifier"
Write-Host ""

Write-Host "[1/5] Running offline tests..." -ForegroundColor Yellow
python -m pytest -q tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "[2/5] Checking pipeline readiness..." -ForegroundColor Yellow
python scripts/pipeline_doctor.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "[3/5] Testing planning LLM..." -ForegroundColor Yellow
python scripts/test_llm.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
if (Test-Path (Join-Path $EpisodeDir "manifest.json")) {
    Write-Host "[4/5] Episode 001 already exists; reusing it." -ForegroundColor Green
}
else {
    Write-Host "[4/5] Generating Episode 001 planning package..." -ForegroundColor Yellow
    python scripts/run_episode.py --input examples/episode_001_fuel_oil_purifier.json
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$ManifestPath = Join-Path $EpisodeDir "manifest.json"
if (-not (Test-Path $ManifestPath)) {
    Write-Host "Episode manifest was not created." -ForegroundColor Red
    exit 1
}

$Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
Write-Host "Episode status: $($Manifest.status)"

if ($Manifest.status -eq "needs_content_revision") {
    Write-Host ""
    Write-Host "Content Reviewer requested revision." -ForegroundColor Red
    Write-Host "Open:"
    Write-Host "  $EpisodeDir\review_report.json"
    Write-Host ""
    Write-Host "Do not spend Flow credits yet."
    exit 2
}

if (-not (Test-Path (Join-Path $EpisodeDir "veo_prompts.json"))) {
    Write-Host ""
    Write-Host "Planning has not reached video prompts yet." -ForegroundColor Red
    Write-Host "Current status: $($Manifest.status)"
    exit 2
}

Write-Host ""
Write-Host "[5/5] Building Google Flow prompt pack..." -ForegroundColor Yellow
python scripts/build_flow_pack.py --episode-id $EpisodeId
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "EPISODE 001 READY FOR FIRST FLOW RENDER" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "1. Review:"
Write-Host "   $EpisodeDir\idea.json"
Write-Host "   $EpisodeDir\script.json"
Write-Host "   $EpisodeDir\review_report.json"
Write-Host ""
Write-Host "2. Create/load the three Flow references from:"
Write-Host "   $EpisodeDir\flow_jobs\REFERENCE_SETUP.md"
Write-Host ""
Write-Host "3. Render ONLY scene_01 using:"
Write-Host "   $EpisodeDir\flow_jobs\scene_01.txt"
Write-Host ""
Write-Host "4. Save the downloaded video exactly as:"
Write-Host "   $EpisodeDir\scenes\scene_01.mp4"
Write-Host ""
Write-Host "5. Then run:"
Write-Host "   python scripts/visual_doctor.py"
Write-Host "   python scripts/review_scene.py --episode-id $EpisodeId --scene scene_01"
Write-Host ""
