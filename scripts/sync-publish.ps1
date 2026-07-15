# Sync monorepo packages -> PyPI/npm publish mirrors in flops_public.
# Run from repo root:  .\scripts\sync-publish.ps1
# Requires: flopsindex/ (this repo) and sibling folders flopsindex-mcp, flopsindex-pysdk, flopsindex-tssdk

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
$PubRoot = Split-Path $Root -Parent

# --- Preflight: fail CLOSED on retired hosts + internal-repo pointers ----------
# This sync is a verbatim Copy-Item pass-through — it does NOT rewrite content.
# So if a forbidden reference leaks into the source tree (e.g. via a manual copy
# from the private dev monorepo, which still carries stale refs), it would ride
# straight to PyPI/npm. This guard catches that before publish.
#
# The forbidden literals (retired subdomains + the private dev-repo path/codename)
# are NOT stored in this public file — not even encoded. They live only in an
# untracked, gitignored local list (scripts/forbidden-patterns.local.txt) so this
# public repo never contains them in any form. On a public checkout that list is
# absent and the guard is simply skipped: it exists to protect the maintainer's
# publish flow, not to run on clones.
$ForbiddenFile = Join-Path $PSScriptRoot 'forbidden-patterns.local.txt'
if (Test-Path $ForbiddenFile) {
    $Forbidden = Get-Content -Path $ForbiddenFile |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith('#') }
} else {
    $Forbidden = @()
    Write-Host "Preflight: no local forbidden-patterns list (scripts/forbidden-patterns.local.txt) — guard skipped." -ForegroundColor Yellow
}
# Skip build artifacts (.egg-info, __pycache__, dist, node_modules, .git, …) —
# they never ship (sync copies an explicit include-list) and a stale artifact
# built from old source would false-abort an otherwise-clean publish. This
# guards SOURCE files, and excludes the gate script itself.
$SkipDirs = '\\(\.git|\.egg-info|[^\\]*\.egg-info|__pycache__|node_modules|dist|dist-check|build|\.pytest_cache)\\'
if ($Forbidden.Count -gt 0) {
    $hits = Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch $SkipDirs -and $_.FullName -ne $PSCommandPath -and $_.FullName -ne $ForbiddenFile } |
        Select-String -Pattern $Forbidden -SimpleMatch -List -ErrorAction SilentlyContinue
    if ($hits) {
        Write-Host "ABORT: forbidden reference(s) found in the source tree:" -ForegroundColor Red
        $hits | ForEach-Object { Write-Host ("  {0}: {1}" -f $_.Path, $_.Line.Trim()) -ForegroundColor Red }
        throw "Preflight failed. Repoint retired hosts to the public GitHub repo and drop any private dev-repo reference before publishing."
    }
    Write-Host "Preflight OK: no retired hosts or internal-repo pointers in the tree." -ForegroundColor Green
}
# ------------------------------------------------------------------------------

function Sync-Tree {
    param(
        [string]$Source,
        [string]$Dest,
        [string[]]$Include
    )
    if (-not (Test-Path $Source)) { throw "Missing source: $Source" }
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    foreach ($item in $Include) {
        $srcPath = Join-Path $Source $item
        $dstPath = Join-Path $Dest $item
        if (-not (Test-Path $srcPath)) { throw "Missing: $srcPath" }
        if (Test-Path $dstPath) {
            Remove-Item -Recurse -Force $dstPath
        }
        $parent = Split-Path $dstPath -Parent
        if ($parent -and -not (Test-Path $parent)) {
            New-Item -ItemType Directory -Force -Path $parent | Out-Null
        }
        Copy-Item -Path $srcPath -Destination $dstPath -Recurse -Force
        Write-Host "  $item"
    }
}

Write-Host "Sync MCP -> flopsindex-mcp"
Sync-Tree (Join-Path $Root "mcp") (Join-Path $PubRoot "flopsindex-mcp") @(
    "flopsindex_mcp",
    "tests",
    "scripts",
    "server.json",
    "pyproject.toml",
    "MANIFEST.in",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "NOTICE"
)

Write-Host "Sync Python SDK -> flopsindex-pysdk"
Sync-Tree (Join-Path $Root "sdk\python") (Join-Path $PubRoot "flopsindex-pysdk") @(
    "flopsindex",
    "tests",
    "pyproject.toml",
    "MANIFEST.in",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "NOTICE"
)

Write-Host "Sync TypeScript SDK -> flopsindex-tssdk (source only)"
$tsSrc = Join-Path $Root "sdk\typescript"
$tsDst = Join-Path $PubRoot "flopsindex-tssdk"
foreach ($item in @("src", "test", "package.json", "package-lock.json", "tsconfig.json", "smoke.ts", "smoke.mjs", "README.md", "CHANGELOG.md", "LICENSE", "NOTICE", ".gitignore")) {
    $srcPath = Join-Path $tsSrc $item
    $dstPath = Join-Path $tsDst $item
    if (-not (Test-Path $srcPath)) { throw "Missing: $srcPath" }
    if (Test-Path $dstPath) { Remove-Item -Recurse -Force $dstPath }
    Copy-Item -Path $srcPath -Destination $dstPath -Recurse -Force
    Write-Host "  $item"
}

function Add-PublishBanner {
    param([string]$ReadmePath, [string]$Banner)
    $text = Get-Content -Raw -Path $ReadmePath
    if ($text -match [regex]::Escape($Banner.Trim())) { return }
    $lines = $text -split "`r?`n", 2
    if ($lines.Count -lt 2) { throw "Unexpected README shape: $ReadmePath" }
    $updated = $lines[0] + "`n`n" + $Banner + "`n`n" + $lines[1]
    Set-Content -Path $ReadmePath -Value $updated -NoNewline
    Write-Host "  banner -> $ReadmePath"
}

Add-PublishBanner (Join-Path $PubRoot "flopsindex-mcp\README.md") @"
> **PyPI release mirror.** Source of truth: [``flopsindex`` monorepo](https://github.com/zeroatflops/flopsindex) (``mcp/``). Refresh with ``flopsindex/scripts/sync-publish.ps1`` before publishing.
"@

Add-PublishBanner (Join-Path $PubRoot "flopsindex-pysdk\README.md") @"
> **PyPI release mirror.** Source of truth: [``flopsindex`` monorepo](https://github.com/zeroatflops/flopsindex) (``sdk/python/``). Refresh with ``flopsindex/scripts/sync-publish.ps1`` before publishing.
"@

Add-PublishBanner (Join-Path $PubRoot "flopsindex-tssdk\README.md") @"
> **npm release mirror.** Source of truth: [``flopsindex`` monorepo](https://github.com/zeroatflops/flopsindex) (``sdk/typescript/``). Refresh with ``flopsindex/scripts/sync-publish.ps1``, then ``npm run build``, before publishing.
"@

Write-Host "Done. Rebuild TS dist in flopsindex-tssdk: npm run build"
