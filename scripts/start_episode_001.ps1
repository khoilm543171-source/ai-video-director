$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$EpisodeId = "episode_001_fuel_oil_purifier"
$EpisodeDir = Join-Path $RepoRoot "outputs\episodes\$EpisodeId"

Write-Host "[1/2] Running offline tests..." -ForegroundColor Yellow
python -m pytest -q tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[2/2] Compiling eight Flow jobs from the approved spec..." -ForegroundColor Yellow
python scripts/build_flow_pack.py --episode-id $EpisodeId
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "EPISODE 001 — 8 FLOW JOBS / 69s FINAL TARGET" -ForegroundColor Green
Write-Host "Read: $EpisodeDir\flow_jobs\START_HERE.md"
Write-Host "Load three reusable references, then generate ONLY scene_01 from scene_01_base.txt."
Write-Host "For scenes longer than 8s use scene_XX_extend.txt on the SAME scene."
Write-Host "Save one final file per scene as $EpisodeDir\scenes\scene_XX.mp4."
Write-Host "After rendering, run: python scripts/check_flow_clips.py --episode-id $EpisodeId"
Write-Host "Then listen to exact words and check mouth sync, identity and continuity before release."
