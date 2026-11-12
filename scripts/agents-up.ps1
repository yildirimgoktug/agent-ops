<#
.SYNOPSIS
  Create one detached git worktree per agent, all from the same base.
.DESCRIPTION
  PowerShell twin of agents-up.sh. Never deletes, resets or pushes anything.
.EXAMPLE
  ./scripts/agents-up.ps1 -Base origin/feat/wave-1 -Dir ..\wt -Names alpha,beta,gamma
.EXAMPLE
  ./scripts/agents-up.ps1 -Base origin/feat/wave-1 -Names alpha,beta -DryRun
#>
param(
  [Parameter(Mandatory = $true)][string]$Base,
  [Parameter(Mandatory = $true)][string[]]$Names,
  [string]$Dir = "..\agent-worktrees",
  [switch]$DryRun
)
$ErrorActionPreference = "Stop"

git rev-parse --is-inside-work-tree 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "run inside a git repository" }
git rev-parse --verify --quiet "$Base^{commit}" | Out-Null
if ($LASTEXITCODE -ne 0) { throw "base '$Base' does not resolve; fetch first?" }

$pushBranch = $Base -replace '^origin/', ''

foreach ($name in $Names) {
  if ($name -notmatch '^[A-Za-z0-9._-]+$') { throw "bad agent name '$name'" }
  $path = Join-Path $Dir $name
  if (Test-Path $path) { Write-Warning "skip: $path already exists"; continue }
  if ($DryRun) {
    Write-Output "would run: git worktree add --detach `"$path`" `"$Base`""
  } else {
    git worktree add --detach $path $Base
    if ($LASTEXITCODE -ne 0) { throw "git worktree add failed for $name" }
  }
}

Write-Output @"

Next, per agent:
  1. Open a separate agent session in its worktree.
  2. Give it its task brief; the brief lists the files it owns.
  3. When done, inside the worktree:
       git add <explicit paths>      # never 'git add -A'
       git commit
       git pull --rebase origin $pushBranch
       git push origin HEAD:$pushBranch   # if rejected: pull --rebase again; never --force
  4. Remove finished worktrees with scripts/agents-down.ps1.
"@
