<#
.SYNOPSIS
  graphify manifest 기준으로 vault/*.md 변경 드리프트(수정+신규)를 계산한다.
  vault-load가 그래프 기반 탐색 결과를 "말없이 낡은 채로" 쓰지 않도록 경고 트리거를 제공한다.

.DESCRIPTION
  manifest 는 조회 대상 graph.json 과 **같은 실행분**이어야 의미가 있다.
  기본값은 vault-load 가 실제로 조회하는 graphify-out/graph.json 과 짝이 맞는
  graphify-out/manifest.json 이다.

  manifest 키 포맷은 graphify 실행 위치에 따라 두 가지가 존재한다:
    - 저장소 루트 실행:  vault\architecture\foo.md
    - vault 안에서 실행: architecture\foo.md
  양쪽 모두 vault 상대경로로 정규화해서 비교한다.

.OUTPUTS
  단일 요약 라인: DRIFT=<n> MODIFIED=<n> NEW=<n> THRESHOLD=<n> STALE=<true|false>
  드리프트가 있으면 이어서 변경 파일 목록(최대 15개)을 출력한다.
  manifest.json이 없으면 NO_MANIFEST를 출력하고 exit 1 (호출측은 이 경우 경고를 생략한다).
  manifest가 graph.json보다 오래됐으면 MANIFEST_OLDER_THAN_GRAPH 경고 라인을 덧붙인다.
#>
param(
    [string]$VaultPath = "vault",
    [string]$ManifestPath = "graphify-out/manifest.json",
    [string]$GraphPath = "graphify-out/graph.json",
    [int]$Threshold = 5
)

if (-not (Test-Path $ManifestPath)) {
    Write-Output "NO_MANIFEST"
    exit 1
}

$manifestJson = Get-Content $ManifestPath -Raw -Encoding utf8 | ConvertFrom-Json

# 키를 vault 상대경로로 정규화 — 선행 vault\ 또는 vault/ 를 제거하고 구분자를 통일한다.
$manifestMap = @{}
$manifestJson.PSObject.Properties | ForEach-Object {
    $key = $_.Name -replace '/', '\'
    $key = $key -replace '^vault\\', ''
    $manifestMap[$key] = $_.Value
}

$vaultFull = (Resolve-Path $VaultPath).Path
$modified = New-Object System.Collections.Generic.List[string]
$new = New-Object System.Collections.Generic.List[string]

Get-ChildItem -Path $VaultPath -Recurse -Filter "*.md" -File |
    Where-Object { $_.FullName -notmatch '\\graphify-out\\' } |
    ForEach-Object {
        $rel = $_.FullName.Substring($vaultFull.Length + 1)
        if ($manifestMap.ContainsKey($rel)) {
            $manifestEpoch = [double]$manifestMap[$rel]
            $manifestUtc = [DateTimeOffset]::FromUnixTimeSeconds([long][math]::Floor($manifestEpoch)).UtcDateTime
            if ($_.LastWriteTimeUtc -gt $manifestUtc.AddSeconds(2)) {
                $modified.Add($rel)
            }
        } else {
            $new.Add($rel)
        }
    }

$drift = $modified.Count + $new.Count
$stale = $drift -ge $Threshold

Write-Output "DRIFT=$drift MODIFIED=$($modified.Count) NEW=$($new.Count) THRESHOLD=$Threshold STALE=$($stale.ToString().ToLower())"

# manifest 와 graph.json 이 다른 실행분이면 드리프트 수치 자체를 믿을 수 없다.
if (Test-Path $GraphPath) {
    $mTime = (Get-Item $ManifestPath).LastWriteTimeUtc
    $gTime = (Get-Item $GraphPath).LastWriteTimeUtc
    if ($mTime -lt $gTime.AddMinutes(-10)) {
        Write-Output "MANIFEST_OLDER_THAN_GRAPH manifest=$($mTime.ToString('yyyy-MM-dd HH:mm')) graph=$($gTime.ToString('yyyy-MM-dd HH:mm'))"
    }
}

if ($drift -gt 0) {
    Write-Output "--- changed since last graphify run ---"
    ($modified + $new) | Select-Object -First 15 | ForEach-Object { Write-Output $_ }
}
