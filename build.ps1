param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }
    & $Python dev/collect_licenses.py
    if ($LASTEXITCODE -ne 0) { throw 'License collection failed' }
    & $Python -m PyInstaller --noconfirm SonyLanguageUnlock.spec
    if ($LASTEXITCODE -ne 0) { throw 'Executable build failed' }
    foreach ($name in 'README.md','README.en.md','GITHUB_UPLOAD.md','THIRD_PARTY.md','VALIDATION.md','FONT_COMPARISON.md','SPONSOR.md') {
        Copy-Item -LiteralPath $name -Destination ('dist/SonyLanguageUnlock/' + $name)
    }
    $sponsorAssets = 'dist/SonyLanguageUnlock/assets/sponsor'
    New-Item -ItemType Directory -Path $sponsorAssets -Force | Out-Null
    foreach ($name in 'wechat.jpg','alipay.jpg','usdt-bsc.png') {
        Copy-Item -LiteralPath ('assets/sponsor/' + $name) -Destination (Join-Path $sponsorAssets $name)
    }
    Copy-Item -LiteralPath licenses -Destination dist/SonyLanguageUnlock/licenses -Recurse -Force
    Write-Host 'Built: dist/SonyLanguageUnlock/SonyLanguageUnlock.exe'
} finally {
    Pop-Location
}
