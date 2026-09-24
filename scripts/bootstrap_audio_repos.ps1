$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VendorRoot = Join-Path $RepoRoot "vendor"

New-Item -ItemType Directory -Force -Path $VendorRoot | Out-Null

$Repos = @(
    @{
        Name = "chatterbox"
        Url = "https://github.com/resemble-ai/chatterbox.git"
        Commit = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"
    },
    @{
        Name = "mmaudio"
        Url = "https://github.com/hkchengrex/MMAudio.git"
        Commit = "974010a026c731054592d8f777218bd9d85a6c24"
    },
    @{
        Name = "ace-step"
        Url = "https://github.com/ace-step/ACE-Step-1.5.git"
        Commit = "ca1e85fe9430179831e6bc6be790c332190a3866"
    },
    @{
        Name = "kokoro-fastapi"
        Url = "https://github.com/remsky/Kokoro-FastAPI.git"
        Commit = "b4ef64b1ce60682debda4fe0a066259e284eb1b4"
    }
)

foreach ($Repo in $Repos) {
    $Target = Join-Path $VendorRoot $Repo.Name

    if (Test-Path (Join-Path $Target ".git")) {
        Write-Host "Updating $($Repo.Name)..."
        git -C $Target fetch --all --tags
    }
    else {
        Write-Host "Cloning $($Repo.Name)..."
        git clone $Repo.Url $Target
    }

    git -C $Target checkout --detach $Repo.Commit
}

Write-Host ""
Write-Host "Pinned audio repositories are ready under: $VendorRoot"
Write-Host "Next: install each model in its own environment/service."
