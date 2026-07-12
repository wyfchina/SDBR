param(
  [string]$BaseUrl = "http://127.0.0.1:8765",
  [string]$OutputPath = ".tmp/mto-order-commitment-browser-fixture.json"
)

$ErrorActionPreference = "Stop"

function Invoke-SdbrJson {
  param(
    [string]$Method,
    [string]$Path,
    [object]$Body = $null,
    [hashtable]$Headers = @{}
  )
  $arguments = @{
    Uri = "$BaseUrl$Path"
    Method = $Method
    Headers = $Headers
    SkipHttpErrorCheck = $true
    SkipHeaderValidation = $true
  }
  if ($null -ne $Body) {
    $arguments.ContentType = "application/json"
    $arguments.Body = $Body | ConvertTo-Json -Depth 30
  }
  $response = Invoke-WebRequest @arguments
  $payload = $response.Content | ConvertFrom-Json
  return [pscustomobject]@{
    StatusCode = [int]$response.StatusCode
    Revision = [string]$response.Headers["X-Workbench-Revision"]
    Payload = $payload
  }
}

function Copy-JsonObject {
  param([object]$Value)
  return $Value | ConvertTo-Json -Depth 30 | ConvertFrom-Json
}

$reset = Invoke-SdbrJson `
  -Method "POST" `
  -Path "/planner/workbench/test-data/order-commitment/reset"
if ($reset.StatusCode -ne 200) {
  throw "MTO fixture reset failed: $($reset.StatusCode)"
}
$template = $reset.Payload.Data.IntakePayloadTemplate

function New-MtoEvaluation {
  param([string]$Suffix)
  $body = Copy-JsonObject $template
  $body.OrderID = "TST-MTO-SO-$Suffix"
  $body.TraceID = "TRACE-TST-MTO-$Suffix"
  $body.MaterialRequirements[0].RequirementLineID = (
    "{0}:10:TST-MTO-RM-1" -f $body.OrderID
  )
  $response = Invoke-SdbrJson `
    -Method "POST" `
    -Path "/planner/workbench/order-commitments/intake" `
    -Body $body
  if ($response.StatusCode -ne 200) {
    throw "MTO intake $Suffix failed: $($response.StatusCode)"
  }
  return $response
}

$ordinary = New-MtoEvaluation "ORDINARY"
$skipSource = New-MtoEvaluation "SKIP"
$stale = New-MtoEvaluation "STALE"
$acceptSource = New-MtoEvaluation "ACCEPT"
$rejectSource = New-MtoEvaluation "REJECT"

$skipSourceId = $skipSource.Payload.Data.Evaluation.EvaluationID
$skipped = Invoke-SdbrJson `
  -Method "POST" `
  -Path (
    "/planner/workbench/order-commitments/{0}/reevaluate" -f
    $skipSourceId
  ) `
  -Body @{
    RequestedBy = "planner-browser"
    OperationalStateSnapshotID = $null
    CheckMaterialAvailability = $false
    MaterialCheckSkipReason = "Browser capacity-only acceptance evidence."
  }
if ($skipped.StatusCode -ne 200) {
  throw "MTO skipped-material re-evaluation failed."
}

$staleId = $stale.Payload.Data.Evaluation.EvaluationID
$originalStaleDetail = Invoke-SdbrJson `
  -Method "GET" `
  -Path (
    "/planner/workbench/order-commitments/{0}" -f $staleId
  )
$staleFingerprint = (
  $originalStaleDetail.Payload.Data.TechnicalDetails.EvaluationFingerprint
)

$acceptId = $acceptSource.Payload.Data.Evaluation.EvaluationID
$acceptDetail = Invoke-SdbrJson `
  -Method "GET" `
  -Path (
    "/planner/workbench/order-commitments/{0}" -f $acceptId
  )
$accepted = Invoke-SdbrJson `
  -Method "POST" `
  -Path (
    "/planner/workbench/order-commitments/{0}/decision" -f $acceptId
  ) `
  -Headers @{ "If-Match" = $acceptDetail.Revision } `
  -Body @{
    DecisionID = "DEC-TST-MTO-BROWSER-ACCEPT"
    Decision = "AcceptRequestedDate"
    DecidedBy = "planner-browser"
    Reason = "Browser acceptance evidence."
    ExpectedEvaluationFingerprint = (
      $acceptDetail.Payload.Data.TechnicalDetails.EvaluationFingerprint
    )
    CcrRiskAcknowledged = $true
    MaterialRiskAcknowledged = $false
  }
if ($accepted.StatusCode -ne 200) {
  throw "MTO acceptance failed."
}

$rejectId = $rejectSource.Payload.Data.Evaluation.EvaluationID
$rejectDetail = Invoke-SdbrJson `
  -Method "GET" `
  -Path ("/planner/workbench/order-commitments/{0}" -f $rejectId)
$rejected = Invoke-SdbrJson `
  -Method "POST" `
  -Path (
    "/planner/workbench/order-commitments/{0}/decision" -f $rejectId
  ) `
  -Headers @{ "If-Match" = $rejectDetail.Revision } `
  -Body @{
    DecisionID = "DEC-TST-MTO-BROWSER-REJECT"
    Decision = "Reject"
    DecidedBy = "planner-browser"
    Reason = "Browser rejected-terminal evidence."
    ExpectedEvaluationFingerprint = (
      $rejectDetail.Payload.Data.TechnicalDetails.EvaluationFingerprint
    )
    CcrRiskAcknowledged = $false
    MaterialRiskAcknowledged = $false
  }
if ($rejected.StatusCode -ne 200) {
  throw "MTO rejection failed."
}

$staleDetail = Invoke-SdbrJson `
  -Method "GET" `
  -Path (
    "/planner/workbench/order-commitments/{0}" -f $staleId
  )
$staleDecision = Invoke-SdbrJson `
  -Method "POST" `
  -Path (
    "/planner/workbench/order-commitments/{0}/decision" -f $staleId
  ) `
  -Headers @{ "If-Match" = $staleDetail.Revision } `
  -Body @{
    DecisionID = "DEC-TST-MTO-BROWSER-STALE"
    Decision = "AcceptRequestedDate"
    DecidedBy = "planner-browser"
    Reason = "Must be rejected as stale."
    ExpectedEvaluationFingerprint = $staleFingerprint
    CcrRiskAcknowledged = $true
    MaterialRiskAcknowledged = $false
  }
if (
  $staleDecision.StatusCode -ne 409 -or
  $staleDecision.Payload.Data.Status -ne "OrderCommitmentEvaluationStale"
) {
  throw "MTO stale-decision fixture did not produce the expected 409."
}

$result = [ordered]@{
  BaselinePlanningRunID = $reset.Payload.Data.BaselinePlanningRunID
  OperationalStateSnapshotID = (
    $reset.Payload.Data.OperationalStateSnapshotID
  )
  OrdinaryEvaluationID = (
    $ordinary.Payload.Data.Evaluation.EvaluationID
  )
  SkippedEvaluationID = (
    $skipped.Payload.Data.Evaluation.EvaluationID
  )
  AcceptedEvaluationID = $acceptId
  AcceptedReservationBatchID = (
    $accepted.Payload.Data.ReservationBatchID
  )
  RejectedEvaluationID = $rejectId
  StaleEvaluationID = $staleId
  StaleDecisionStatus = $staleDecision.Payload.Data.Status
  FinalRevision = $staleDecision.Revision
}
$directory = Split-Path -Parent $OutputPath
if ($directory) {
  New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
$result | ConvertTo-Json -Depth 10 |
  Set-Content -LiteralPath $OutputPath -Encoding utf8
$result
