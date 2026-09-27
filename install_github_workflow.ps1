$destination = Join-Path $PSScriptRoot '.github/workflows'
New-Item -ItemType Directory -Force -Path $destination | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'github-workflows/update-and-deploy.yml') (Join-Path $destination 'update-and-deploy.yml') -Force
Write-Host 'GitHub Actions workflow installed. Commit and push the .github folder.'
