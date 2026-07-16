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

function Assert-Equal {
  param(
    [string]$Label,
    [object]$Actual,
    [object]$Expected
  )
  if ($Actual -ne $Expected) {
    throw "$Label expected '$Expected' but got '$Actual'."
  }
}

function Assert-True {
  param(
    [string]$Label,
    [bool]$Condition
  )
  if (-not $Condition) {
    throw "$Label expected true but got false."
  }
}

$reset = Invoke-SdbrJson `
  -Method "POST" `
  -Path "/planner/workbench/test-data/order-commitment/reset"
if ($reset.StatusCode -ne 200) {
  throw "MTO fixture reset failed: $($reset.StatusCode)"
}
$template = $reset.Payload.Data.IntakePayloadTemplate

function New-MtoEvaluation {
  param(
    [string]$Suffix,
    [double]$Quantity,
    [double]$RequiredQty
  )
  $body = Copy-JsonObject $template
  $body.OrderID = "TST-MTO-SO-$Suffix"
  $body.TraceID = "TRACE-TST-MTO-$Suffix"
  $body.Quantity = $Quantity
  $body.MaterialRequirements[0].RequiredQty = $RequiredQty
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

function Get-MtoEvaluationDetail {
  param([string]$EvaluationID)
  $response = Invoke-SdbrJson `
    -Method "GET" `
    -Path (
      "/planner/workbench/order-commitments/{0}" -f $EvaluationID
    )
  if ($response.StatusCode -ne 200) {
    throw "MTO detail $EvaluationID failed: $($response.StatusCode)"
  }
  return $response
}

function Get-MaxWindowValue {
  param(
    [object]$Detail,
    [string]$Property
  )
  $windows = @(
    $Detail.Payload.Data.CapacityEvidence.SelectedAssessment.WindowAssessments
  )
  if ($windows.Count -eq 0) {
    throw "MTO detail has no selected CCR capacity window."
  }
  return [double](
    ($windows | Measure-Object -Property $Property -Maximum).Maximum
  )
}

$businessCases = @(
  @{
    Suffix = "ON-TIME-REFERENCE"
    Quantity = 1
    RequiredQty = 5
    ExpectedCapacityStatus = "OnTime"
    ExpectedMaterialStatus = "Feasible"
    ExpectedThresholdState = "ReferenceFallback"
    ExpectedRecommendation = "PlannerConfirmationRequired"
    ExpectedLoadBeforeMinutes = 180
    ExpectedLoadAfterMinutes = 240
    ExpectedLoadAfterPercent = 50
  },
  @{
    Suffix = "OVER-PROTECTION"
    Quantity = 4
    RequiredQty = 20
    ExpectedCapacityStatus = "OnTime"
    ExpectedMaterialStatus = "Feasible"
    ExpectedThresholdState = "ReferenceFallback"
    ExpectedRecommendation = "PlannerConfirmationRequired"
    ExpectedLoadBeforeMinutes = 180
    ExpectedLoadAfterMinutes = 420
    ExpectedLoadAfterPercent = 87.5
  },
  @{
    Suffix = "LATER-SAFE-DATE"
    Quantity = 6
    RequiredQty = 30
    ExpectedCapacityStatus = "LaterSafeDate"
    ExpectedMaterialStatus = "Feasible"
    ExpectedThresholdState = "ReferenceFallback"
    ExpectedRecommendation = "PlannerConfirmationRequired"
  },
  @{
    Suffix = "MATERIAL-SHORTAGE"
    Quantity = 1
    RequiredQty = 120
    ExpectedCapacityStatus = "OnTime"
    ExpectedMaterialStatus = "Shortage"
    ExpectedThresholdState = "ReferenceFallback"
    ExpectedRecommendation = "DoNotRecommendAccept"
  },
  @{
    Suffix = "MATERIAL-SKIPPED"
    Quantity = 1
    RequiredQty = 5
    ExpectedCapacityStatus = "OnTime"
    ExpectedMaterialStatus = "SkippedPendingConfirmation"
    ExpectedThresholdState = "ReferenceFallback"
    ExpectedRecommendation = "PlannerConfirmationRequired"
    SkipMaterial = $true
  }
)

$businessResponses = @{}
foreach ($case in $businessCases) {
  $businessResponses[$case.Suffix] = New-MtoEvaluation `
    -Suffix $case.Suffix `
    -Quantity $case.Quantity `
    -RequiredQty $case.RequiredQty
}

$skipCase = $businessCases |
  Where-Object { $_.Suffix -eq "MATERIAL-SKIPPED" }
$skipSourceId = (
  $businessResponses[$skipCase.Suffix].Payload.Data.Evaluation.EvaluationID
)
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
    MaterialCheckSkipReason = (
      "Planner requested capacity-only MTO evaluation."
    )
  }
if ($skipped.StatusCode -ne 200) {
  throw "MTO skipped-material re-evaluation failed."
}
$businessResponses[$skipCase.Suffix] = $skipped

$businessEvidence = @()
foreach ($case in $businessCases) {
  $summary = $businessResponses[$case.Suffix]
  $evaluationId = $summary.Payload.Data.Evaluation.EvaluationID
  $detail = Get-MtoEvaluationDetail -EvaluationID $evaluationId
  $data = $detail.Payload.Data

  Assert-Equal `
    "$($case.Suffix) capacity" `
    $data.CapacityEvidence.Status `
    $case.ExpectedCapacityStatus
  Assert-Equal `
    "$($case.Suffix) material" `
    $data.MaterialEvidence.Status `
    $case.ExpectedMaterialStatus
  Assert-Equal `
    "$($case.Suffix) threshold" `
    $data.Recommendation.ThresholdState `
    $case.ExpectedThresholdState
  Assert-Equal `
    "$($case.Suffix) recommendation" `
    $data.Recommendation.Decision `
    $case.ExpectedRecommendation

  $loadBeforeMinutes = Get-MaxWindowValue `
    -Detail $detail `
    -Property "LoadBeforeMinutes"
  $loadAfterMinutes = Get-MaxWindowValue `
    -Detail $detail `
    -Property "LoadAfterMinutes"
  $loadAfterPercent = Get-MaxWindowValue `
    -Detail $detail `
    -Property "LoadAfterPercent"

  if ($case.ContainsKey("ExpectedLoadBeforeMinutes")) {
    Assert-Equal `
      "$($case.Suffix) load before" `
      $loadBeforeMinutes `
      ([double]$case.ExpectedLoadBeforeMinutes)
    Assert-Equal `
      "$($case.Suffix) load after" `
      $loadAfterMinutes `
      ([double]$case.ExpectedLoadAfterMinutes)
    Assert-Equal `
      "$($case.Suffix) load percent" `
      $loadAfterPercent `
      ([double]$case.ExpectedLoadAfterPercent)
  }

  if ($case.Suffix -eq "LATER-SAFE-DATE") {
    $requestedPromiseAt = [DateTimeOffset]::Parse(
      $data.CapacityEvidence.RequestedDateAssessment.PromiseAt
    )
    $safePromiseAt = [DateTimeOffset]::Parse(
      $data.CapacityEvidence.EarliestSafeAssessment.PromiseAt
    )
    Assert-True `
      "$($case.Suffix) safe promise is later" `
      ($safePromiseAt -gt $requestedPromiseAt)
  }

  if ($case.Suffix -eq "MATERIAL-SKIPPED") {
    Assert-Equal `
      "$($case.Suffix) material check" `
      $data.MaterialEvidence.CheckEnabled `
      $false
    Assert-True `
      "$($case.Suffix) skip reason" `
      (-not [string]::IsNullOrWhiteSpace($data.MaterialEvidence.SkipReason))
  }

  $businessEvidence += [ordered]@{
    OrderID = $data.Order.OrderID
    EvaluationID = $data.EvaluationID
    Quantity = $case.Quantity
    RequiredMaterialQty = $case.RequiredQty
    CapacityStatus = $data.CapacityEvidence.Status
    MaterialStatus = $data.MaterialEvidence.Status
    ThresholdState = $data.Recommendation.ThresholdState
    Recommendation = $data.Recommendation.Decision
    RequestedPromiseAt = (
      $data.CapacityEvidence.RequestedDateAssessment.PromiseAt
    )
    EarliestSafePromiseAt = (
      $data.CapacityEvidence.EarliestSafeAssessment.PromiseAt
    )
    SelectedPromiseAt = (
      $data.CapacityEvidence.SelectedAssessment.PromiseAt
    )
    LoadBeforeMinutes = $loadBeforeMinutes
    LoadAfterMinutes = $loadAfterMinutes
    LoadAfterPercent = $loadAfterPercent
    MaterialCheckEnabled = $data.MaterialEvidence.CheckEnabled
  }
}

$stale = New-MtoEvaluation `
  -Suffix "FLOW-STALE" `
  -Quantity 1 `
  -RequiredQty 5
$acceptSource = New-MtoEvaluation `
  -Suffix "FLOW-ACCEPT" `
  -Quantity 1 `
  -RequiredQty 5
$rejectSource = New-MtoEvaluation `
  -Suffix "FLOW-REJECT" `
  -Quantity 1 `
  -RequiredQty 5

$staleId = $stale.Payload.Data.Evaluation.EvaluationID
$originalStaleDetail = Get-MtoEvaluationDetail -EvaluationID $staleId
$staleFingerprint = (
  $originalStaleDetail.Payload.Data.TechnicalDetails.EvaluationFingerprint
)

$acceptId = $acceptSource.Payload.Data.Evaluation.EvaluationID
$acceptDetail = Get-MtoEvaluationDetail -EvaluationID $acceptId
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
$rejectDetail = Get-MtoEvaluationDetail -EvaluationID $rejectId
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

$staleDetail = Get-MtoEvaluationDetail -EvaluationID $staleId
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
  BusinessScenarios = $businessEvidence
  LifecycleScenarios = @(
    [ordered]@{
      OrderID = "TST-MTO-SO-FLOW-ACCEPT"
      EvaluationID = $acceptId
      Status = "Accepted"
      ReservationBatchID = $accepted.Payload.Data.ReservationBatchID
      PlanningRunID = $accepted.Payload.Data.PlanningRunID
    },
    [ordered]@{
      OrderID = "TST-MTO-SO-FLOW-REJECT"
      EvaluationID = $rejectId
      Status = "Rejected"
    },
    [ordered]@{
      OrderID = "TST-MTO-SO-FLOW-STALE"
      EvaluationID = $staleId
      Status = $staleDecision.Payload.Data.Status
    }
  )
  FinalRevision = $staleDecision.Revision
}
$directory = Split-Path -Parent $OutputPath
if ($directory) {
  New-Item -ItemType Directory -Path $directory -Force | Out-Null
}
$result | ConvertTo-Json -Depth 30 |
  Set-Content -LiteralPath $OutputPath -Encoding utf8
$result
