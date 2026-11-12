<#
.SYNOPSIS
  Remove agent worktrees, but only ones that lose nothing.
.DESCRIPTION
  PowerShell twin of agents-down.sh. Default is a dry run.
  Run it from a PowerShell prompt. Pass several names as a comma-separated
  list (-Names alpha,beta); a single "alpha,beta" string is split on commas.
  -Yes    remove worktrees that are clean AND fully pushed
  -Force  also remove dirty or unpushed worktrees (their work is LOST)
  Branches are never deleted.
.EXAMPLE
  ./scripts/agents-down.ps1 -Dir ..\wt -Names alpha,beta
.EXAMPLE
  ./scripts/agents-down.ps1 -Dir ..\wt -Names alpha,beta -Yes
#>
param(
  [Parameter(Mandatory = $true)][string[]]$Names,
  [string]$Dir = "..\agent-worktrees",
  [switch]$Yes,
  [switch]$Force
)
$ErrorActionPreference = "Stop"
$Names = @($Names | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$failed = $false
if ($Force) { $Yes = $true }

git rev-parse --is-inside-work-tree 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { throw "run inside a git repository" }

foreach ($name in $Names) {
  $path = Join-Path $Dir $name
  if (-not (Test-Path $path)) { Write-Output "${name}: no worktree at $path"; continue }

  $dirty = @(git -C $path status --porcelain).Where({ $_ }).Count
  $unpushed = @(git -C $path rev-list HEAD --not --remotes).Where({ $_ }).Count
  $state = "clean"
  if ($dirty -gt 0) { $state = "$dirty uncommitted change(s)" }
  if ($unpushed -gt 0) { $state = "$state; $unpushed commit(s) on no remote" }
  elseif ($dirty -eq 0) { $state = "$state, fully pushed" }

  if ($dirty -eq 0 -and $unpushed -eq 0) {
    if ($Yes) {
      git worktree remove $path
      if ($LASTEXITCODE -eq 0) { Write-Output "${name}: removed ($state)" }
      else { [Console]::Error.WriteLine("${name}: FAILED"); $failed = $true }
    } else { Write-Output "${name}: $state - would remove (pass -Yes)" }
  } elseif ($Force) {
    git worktree remove --force $path
    if ($LASTEXITCODE -eq 0) { Write-Output "${name}: FORCE-removed ($state)" }
    else { [Console]::Error.WriteLine("${name}: FAILED"); $failed = $true }
  } else {
    Write-Output "${name}: KEPT - $state. Push or archive it first, or pass -Force to discard."
  }
}

if ($Yes) { git worktree prune }
if ($failed) { exit 1 }
