<#
.SYNOPSIS
  vault-evolve 실행이 필요한 시점인지 판정한다 (경과일 기준 + promote_candidate 누적 기준).
  vault-sync가 매 실행마다 이 스크립트를 호출해 "추천" 메시지를 띄우는 데 사용한다.
  실제 evolve 실행(승격/모순 정리는 승인 게이트 포함)은 여전히 사람이 트리거한다 — 이 스크립트는 판정만 한다.

.OUTPUTS
  단일 요약 라인:
    DUE=<true|false> DAYS_SINCE=<n> LAST_DATE=<yyyy-MM-dd> PROMOTE_COUNT=<n> THRESHOLD_DAYS=<n> THRESHOLD_PROMOTE=<n>
  또는 최초 실행 기록이 없으면:
    DUE=true REASON=no_prior_run PROMOTE_COUNT=<n>
#>
param(
    [string]$EvolveLogPath = "vault/.evolve-log",
    [string]$VaultPath = "vault",
    [int]$DaysThreshold = 7,
    [int]$PromoteThreshold = 3
)

$lastDate = $null
if (Test-Path $EvolveLogPath) {
    $lastLine = Get-Content $EvolveLogPath -Encoding utf8 | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1
    if ($lastLine -match '(\d{4}-\d{2}-\d{2})') {
        $lastDate = [datetime]::ParseExact($matches[1], 'yyyy-MM-dd', $null)
    }
}

$promoteCount = 0
if (Test-Path $VaultPath) {
    Get-ChildItem -Path $VaultPath -Recurse -Filter "*.md" -File |
        Where-Object { $_.FullName -notmatch '\\graphify-out\\' -and $_.FullName -notmatch '\\_templates\\' } |
        ForEach-Object {
            $head = Get-Content $_.FullName -TotalCount 15 -Encoding utf8
            if ($head -match 'promote_candidate:\s*true') {
                $promoteCount++
            }
        }
}

if ($null -eq $lastDate) {
    Write-Output "DUE=true REASON=no_prior_run PROMOTE_COUNT=$promoteCount"
    exit 0
}

# 실행 시점의 실제 시각 기준 경과일 계산 — 이 값은 스크립트가 매번 새로 평가해야 의미가 있으므로
# 시스템 시계(Get-Date)를 쓰는 것이 맞다 (LLM이 문서에 날짜를 "적어 넣는" 경우와는 다른 상황).
$today = Get-Date
$daysSince = [math]::Floor(($today - $lastDate).TotalDays)
$due = ($daysSince -ge $DaysThreshold) -or ($promoteCount -ge $PromoteThreshold)

Write-Output "DUE=$($due.ToString().ToLower()) DAYS_SINCE=$daysSince LAST_DATE=$($lastDate.ToString('yyyy-MM-dd')) PROMOTE_COUNT=$promoteCount THRESHOLD_DAYS=$DaysThreshold THRESHOLD_PROMOTE=$PromoteThreshold"
