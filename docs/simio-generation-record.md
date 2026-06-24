# Simio Generation Record

This document records Simio model generation and mutation workflows so they can later be promoted into a Codex Skill.

## Working Principles

- Record every Simio model generation or mutation step here, including source model, changed tables, changed embedded files, validation scripts, and known limitations.
- Before making assumptions about Simio API, XML, server connector, or headless execution behavior, inspect the local references under `model/`.
- Reference priority:
  1. Local-only `model/Simio API Reference Guide.pdf` when present
  2. Local-only `model/Simio Reference Guide.pdf` when present
  3. Local-only `model/Simio Server Connector Reference.pdf` when present
  4. Existing tracked `.spfx` / XML prototypes under `model/`
- Simio official PDFs are intentionally ignored by Git because of file size; record the expected local paths, but do not commit the PDFs.
- Keep generated model content testable by automated XML/table checks, not only manual Simio UI inspection.

## 2026-06-23 Simple DBR XML Template Completion

Source model:

- `model/Simple_DBR_XML/SDBR_Example.xml`
- Backup observed: `model/Simple_DBR_XML/SDBR_Example.backup`

Goal:

- Complete a first-version Simple DBR Simio template for SDBR schedule validation.
- Do not implement Experiment configuration or headless execution.

Key decisions:

- Resource IDs use underscores, matching Simio object naming:
  - `TST_WC_PREP`
  - `TST_WC_DRUM`
  - `TST_WC_ALT_DRUM`
  - `TST_WC_PAINT`
  - `TST_WC_ASSY`
  - `TST_WC_PACK`
- Product and work order IDs keep business hyphens:
  - `TST-FG-A/B/C`
  - `TST-WO-*`
- `5DayWeek` is the temporary schedule for all Simio resources.
- Operation times are deterministic and stored in `Routings.ProcessTime`.
- DRUM alternate routing remains represented by `TST_ALT_DRUM_NODE` plus `RoutingDestinations`.
- Dispatch Priority is intentionally deferred.

Changed embedded Simio files:

- `Models\Model\TableData\Resources.xml`
- `Models\Model\TableData\Routings.xml`
- `Models\Model\TableData\ManufacturingOrders.xml`
- `Models\Model\08358427-0097-42e8-b044-3ebfe2d801f5.xml`

Mutation technique:

- Parse outer Simio project XML with namespace `http://www.simio.com/projects/v1`.
- Locate embedded `<File>` entries.
- Decode `<BinaryData>` from base64.
- Modify the target embedded XML text.
- Re-encode modified text as base64.
- Write the outer project XML back.

Validation added:

- `tests/test_simio_model_template.py`

Validation coverage:

- Resources use underscore IDs.
- `Resources.WorkSchedule` is `5DayWeek`.
- `TST-FG-A/B/C` routes exist and end at `TST_SINK`.
- Fixed process times match the current SDBR baseline routing times.
- `RoutingDestinations` preserves `TST_ALT_DRUM_NODE -> Input@TST_WC_DRUM / Input@TST_WC_ALT_DRUM`.
- Main process time no longer uses `Random.Triangular(.8, 1, 1.2)` as the APS validation path.

Verification run:

- `python -m compileall -q sdbr`
- `pytest tests/test_simio_model_template.py -q`
- `pytest -q --basetemp .tmp/pytest-simio-full -p no:cacheprovider`

Known limitations:

- No headless Simio submission yet.
- No Experiment generation.
- No Simio result ingestion.
- No APS output package to Simio input table writer yet.
- Random disturbance mode is deferred; current template is deterministic for first-pass validation.

Future Skill Candidate Steps:

1. Inspect local Simio reference PDFs and existing XML prototypes.
2. Decode `.spfx` / XML embedded files.
3. Identify editable `TableData` files.
4. Apply SDBR-to-Simio ID mapping.
5. Write resources, routes, orders, schedules, and optional plan-output tables.
6. Re-encode XML and verify with table-level tests.
7. Optionally invoke headless Simio once API/connector behavior is confirmed from local references.

## 2026-06-23 Simio Validation Loop V1

Source references:

- Local-only `model/Simio API Reference Guide.pdf` when present
- `https://github.com/SimioLLC/SimioApiHelper`
- Local API assembly: `D:\Program Files\Simio LLC\Simio\SimioAPI.dll`
- Local license service executable: `D:\Program Files\Simio LLC\RLM\rlm.exe`
- Template package: `model/SDBR_Example.spfx`

Goal:

- Generate a Simio validation package from an SDBR Completed Planning Run and internal output package.
- Complete a repeatable validation loop with Mock Runner.
- Prepare the local headless path by recording RLM and Simio API prerequisites without pretending full headless execution is complete.

Key decisions:

- `.spfx` is the primary writable package format for V1 because table files are directly addressable inside the zip archive.
- `model/Simple_DBR_XML/SDBR_Example.xml` remains a human/debug reference.
- The internal output package is the source of truth for Simio validation package generation.
- APS-selected resources are preserved; Simio must not rewrite resource choices in this validation loop.
- `runner_mode=mock` is the repeatable product baseline.
- `runner_mode=local` detects/starts RLM and checks local Simio API availability, but the first V1 implementation returns structured `Unavailable` until the local helper is explicitly enabled.
- `runner_mode=auto` falls back to Mock Runner if Local Runner is unavailable.

Generated package tables:

- `Models/Model/TableData/Resources.xml`
- `Models/Model/TableData/Routings.xml`
- `Models/Model/TableData/ManufacturingOrders.xml`

Runtime record:

- `POST /planner/workbench/simio/validation-runs` creates a validation run.
- `GET /planner/workbench/simio/validation-runs/{validation_run_id}` reads the durable validation run.
- `GET /planner/workbench/schedule-results/runs/{run_id}/simio-validation` reads the latest validation summary for a Planning Run.
- Schedule output governance includes the latest Simio validation status, runner backend, package ID, model path, RLM status and KPI summary.

Validation added:

- `tests/test_simio_validation.py`

Validation coverage:

- Generated `.spfx` contains Resources, Routings and ManufacturingOrders table files.
- Generated resource IDs use underscores.
- Generated resources bind `WorkSchedule=5DayWeek`.
- Generated routings are derived from APS operation order and end at `TST_SINK`.
- Mock Runner returns structured Completed or Failed results.
- RLM detection reports `AlreadyRunning` without attempting to start a second process.
- API creation persists validation runs and exposes them through schedule governance.
- Incomplete Planning Runs are rejected with structured `SimioValidationUnavailable`.

Known limitations:

- Local Simio Headless helper was enabled later in this document.
- No Experiment configuration.
- No Dispatch Priority table generation.
- No stochastic disturbance mode.
- No Portal / Server Connector publish path.
- No real Simio throughput, queue, WIP, bottleneck or adjustment recommendation ingestion yet.

## 2026-06-23 Local Headless Helper Enabled

Source references:

- Local-only `model/Simio API Reference Guide.pdf` when present
- `https://github.com/SimioLLC/SimioApiHelper`
- Local API assembly: `D:\Program Files\Simio LLC\Simio\SimioAPI.dll`
- Local runtime: `D:\Program Files\Simio LLC\Simio\Simio.runtimeconfig.json`

Implementation:

- Added `tools/simio_headless_helper/Program.cs`.
- Added `tools/simio_headless_helper/compile.ps1`.
- The helper runs on .NET 10 using `dotnet exec`.
- The helper loads:
  - `SimioAPI.dll`
  - `Simio.dll`
  - `SimioDLL.dll`
- The helper locates `SimioAPI.SimioProjectFactory`.
- Confirmed factory methods:
  - `LoadProject(string)`
  - `LoadProject(string, string[] byref)`
  - `SaveProject(ISimioProject, string, string[] byref)`
  - `IsLicensed`
  - `Shutdown`
- The helper opens the generated `.spfx`, reads the first model through `ISimioProject.Models`, gets `IModel.Plan`, and invokes `RunPlan(RunPlanOptions)` with `AllowDesignErrors=true`.

Important runtime fix:

- Simio initially failed with access denied under the default user temp path:
  - `C:\Users\wyfch\AppData\Local\Temp\Simio\Temp\*.tmp`
- The helper now redirects `TEMP` and `TMP` to:
  - `D:\Documents\SDBR\.tmp\simio-temp`

RLM behavior:

- `rlm.exe` must be running before local headless validation.
- `sdbr/simio_validation.py` now checks existing RLM processes using `tasklist`, with PowerShell `Get-Process` fallback because `tasklist` can return access denied.
- The system does not intentionally stop RLM.

Validation evidence:

- Direct helper run:
  - `dotnet exec .tmp\simio-headless-helper\SimioHeadlessHelper.dll --mode run-plan --model D:\Documents\SDBR\model\SDBR_Example.spfx --temp D:\Documents\SDBR\.tmp\simio-temp`
  - Result: `Status=Completed`, `Message=Simio Plan.RunPlan completed.`, `ProjectName=SDBR_Example`, `ModelName=ModelEntity`
- API local run:
  - `POST /planner/workbench/simio/validation-runs`
  - Payload used `RunnerMode=local`
  - Result: `Status=Completed`, `Runner=local`, `PlanRunCompleted=true`, `RlmStatus=AlreadyRunning`

Known limitations after enabling local helper:

- No Experiment configuration.
- No Dispatch Priority table generation.
- No stochastic disturbance mode.
- No Portal / Server Connector publish path.
- No real Simio throughput, queue, WIP, bottleneck or adjustment recommendation ingestion yet.
- Local helper currently runs `Plan.RunPlan`; it does not yet export Simio logs back into SDBR business KPIs.

## 2026-06-23 XML Template Source and Result Feedback Upgrade

Source references:

- Default source template: `model/Simple_DBR_XML/SDBR_Example.xml`
- Historical/debug package: `model/SDBR_Example.spfx`
- Local helper: `tools/simio_headless_helper/Program.cs`
- API implementation: `sdbr/simio_validation.py`
- General skill: `C:\Users\wyfch\.codex\skills\simio-integration-guide`

Goal:

- Use the SDBR-generated Simio XML project export as the authoritative validation template.
- Generate a derived `.spfx` package from that XML export.
- Run Local Headless Simio on the derived package.
- Save the post-run result package and map available Simio results back into SDBR.

Key implementation:

- `SIMIO_TEMPLATE_PATH` now defaults to `model/Simple_DBR_XML/SDBR_Example.xml`.
- The XML export converter:
  - Parses the outer Simio project XML with namespace `http://www.simio.com/projects/v1`.
  - Finds the nested `<Files>` section under `CommonItems`.
  - Decodes each embedded `<File Name="..."><BinaryData>...` entry.
  - Writes the outer project without the embedded `<Files>` section as `Project.xml`.
  - Writes decoded embedded files into a `.spfx` zip package using normalized `/` paths.
  - Replaces `Resources.xml`, `Routings.xml` and `ManufacturingOrders.xml` with the SDBR validation package rows.
- Validation package generation now keeps template resources as the baseline and merges APS-used resources into it. This is required because Simio resource objects such as `TST_WC_PREP` still initialize even when a specific APS output package does not schedule work on them.
- The local helper must select the business model named `Model`, not the first model in the project. Simio XML exports include `ModelEntity` before the runnable main model; selecting the first model can produce misleading no-flow or incomplete validation results.
- APS timestamps are mapped to the Simio template run horizon. The package records `TimeMapping` with `ApsAnchorAt`, `SimioAnchorAt`, and `OffsetMinutes`; generated `ManufacturingOrders` dates are shifted so releases occur inside the template `RunSetup` window while preserving APS relative timing.
- The package metadata now includes:
  - `TemplateSourcePath`
  - `TemplateSourceType`
  - `TemplateConversion`
  - `ResultModelPath`

Headless helper changes:

- Added `--source` as the primary input path, while preserving `--model` compatibility.
- Added `--output` to save the result model after `Plan.RunPlan`.
- Confirmed direct XML source smoke: `SimioProjectFactory.LoadProject` can load `model/Simple_DBR_XML/SDBR_Example.xml`, run `Plan.RunPlan`, and save `.tmp/simio-validation-smoke/xml-direct-result.spfx`.
- Returned structured fields:
  - `SourceTemplatePath`
  - `GeneratedModelPath`
  - `ResultModelPath`
  - `ResultModelSaved`
  - `PlanRunCompleted`

Result feedback mapping:

- SDBR now returns a unified Simio feedback structure:
  - `FeasibilityConclusion`
  - `Throughput`
  - `QueueMetrics`
  - `WipMetrics`
  - `ResourceUtilization`
  - `ScheduleAdherence`
  - `ResultCoverage`
- `ManufacturingOrdersOutput.xml` is parsed when populated.
- `Results/Model/TableStates.sqlite` is now parsed for the runtime state of
  `Table_ManufacturingOrdersOutput_States_InteractiveValues`; this is the more
  reliable source for post-RunPlan order/resource start-end state when the XML
  table rows are still empty.
- `Results/Model/Interactive_Results.stats` is now parsed by the local helper
  through Simio's own `Simio.Containers.StatisticsReturnValue.CreateFromByteStream`
  method. The helper returns JSON rows with `ObjectName`, `DataSource`,
  `StatisticCategory`, `StatisticType`, `DataItem`, `Value`, `Average`,
  `Minimum`, and `Maximum`.
- Simio result log files are detected and summarized:
  - `Results/Model/Interactive_Results.stats`
  - `Results/Model/ResourceUsage.log`
  - `Results/Model/ResourceState.log`
  - `Results/Model/ResourceCapacity.log`
  - `Results/Model/Task.log`
  - `Results/Model/TaskState.log`
- Queue/WIP/resource metrics are primarily mapped from `Interactive_Results.stats`
  when that file is present. When it is missing, the local helper now enumerates
  post-run Simio log objects directly and aggregates resource utilization from
  `ResourceStateLog` and `ResourceCapacityLog`.
- Post-run resource-state intervals are clipped to the inferred run horizon
  because Simio can include trailing sentinel-like state intervals after the
  planned horizon.
- Queue and system WIP remain partial unless `Interactive_Results.stats`, model
  output tables, or a mapped post-run log source provides explicit values.
- Dedicated input queue-only curves are still not separated. The current queue
  readback uses station content and time-in-station statistics, and labels that
  basis explicitly.
- For `Plan.RunPlan`, `ManufacturingOrdersOutput` values may be stored in
  `Results/Model/TableStates.sqlite` under
  `Table_ManufacturingOrdersOutput_States_PlanValues`. The XML table rows and
  `InteractiveValues` can remain empty even when Plan output exists. SDBR now
  reads `PlanValues` first, maps Simio row-index foreign keys back to
  `ManufacturingOrders.OrderId` and `Routings.RoutingKey`, then falls back to
  `InteractiveValues` and XML rows.

Local smoke evidence:

- Source template: `model/Simple_DBR_XML/SDBR_Example.xml`
- Generated model: `.tmp/simio-validation-smoke-metrics/RUN-SIMIO/SDBR_Example_RUN-SIMIO.spfx`
- Result model: `.tmp/simio-validation-smoke-metrics/RUN-SIMIO/SDBR_Example_RUN-SIMIO_result.spfx`
- Runner: `local`
- Current result:
  - Package generation verifies `TimeMapping` from APS `2026-06-23T06:00:00`
    to Simio `2019-12-02T08:00:00`.
  - Generated `Resources.xml` contains the full template resource set plus APS
    scheduled resources.
  - After restarting the local Simio license service, Local Headless `RunPlan`
    completed from the time-mapped XML-derived package.
  - `Status=Completed`
  - `FeasibilityConclusion=FeasibleWithWarnings`
  - `ResourceUtilization=ParsedFromPostRunLogs`
  - `TST_WC_DRUM UtilizationPercent=34.2045`, `BusyMinutes=3612`,
    `StarvedMinutes=6948`
  - `TST_WC_PACK UtilizationPercent=17.1591`, `BusyMinutes=1812`,
    `StarvedMinutes=8748`
  - `PostRunLogSummary`: `ResourceStateLog=537`, `ResourceCapacityLog=537`,
    `ResourceUsageLog=2`, `TaskLog=6`, `TaskStateLog=50`, `TargetResults=2`
  - `ManufacturingOrdersOutput.xml` is present with two rows but still has no
    populated completion values. The populated plan output is instead in
    `TableStates.sqlite:PlanValues`.
  - `Throughput=Parsed`, `CompletedOrderCount=1`, `UnfinishedOrderCount=0`,
    `OutputSource=Results/Model/TableStates.sqlite:PlanValues`.
  - `ScheduleAdherence=Parsed`; rows map back to `TST-WO-100`,
    `TST-FG-A-10` on `TST_WC_DRUM` and `TST-FG-A-20` on `TST_WC_PACK`.
  - `Interactive_Results.stats` is not saved in the result package, so queue and
    WIP metrics remain partial until a stats export, model output table, or
    mapped post-run queue/WIP log is added.
- Additional finding: `Routings.ProcessTime` is a Simio `UnitType=Time` field.
  Current APS values are minute counts, but Simio interpreted values such as
  `60` as model time units, producing multi-day plan output. The next model
  generation pass should either write process times in the Simio model base unit
  or include an explicit unit conversion.

Known limitations:

- Dedicated input queue length, WIP time curves, bottleneck feedback and action
  recommendations are not fully decoded yet.
- Current result ingestion gives truthful structured coverage: resource
  utilization from post-run Simio logs, plan output from
  `TableStates.sqlite:PlanValues`, and binary/log presence as supporting
  evidence.
- Simio validation remains optional evidence and does not yet gate plan publication.

## 2026-06-23 SDBR Process Feedback Chain

Reference inspected:

- `D:\Program Files\Simio LLC\Simio\Examples\DDMRPExample.spfx`
- Focus: `Models/Model/Processes/MfgStart.xml`,
  `Component_MfgEnd.xml`, `AtEndOfRun.xml`, sched-server processing task
  properties, and `ManufacturingOrdersOutput` runtime table state.

Finding:

- The official DDMRP model writes important business facts through Process
  steps and object add-on hooks, not only static table rows.
- `MfgStart` adds or updates manufacturing-order runtime state and increments
  WIP.
- `Component_MfgEnd` writes completion time and completion status.
- `AtEndOfRun` creates a run-end table summary.
- `ManufacturingOrdersOutput.xml` can remain visually sparse while
  `TableStates.sqlite:PlanValues` contains the actual plan/run output.

Template changes:

- Source template: `model/Simple_DBR_XML/SDBR_Example.xml`
- Added embedded process files:
  - `Models\Model\Processes\SDBR_MfgStart.xml`
  - `Models\Model\Processes\SDBR_OperationStart.xml`
  - `Models\Model\Processes\SDBR_OperationEnd.xml`
  - `Models\Model\Processes\SDBR_MfgEnd.xml`
  - `Models\Model\Processes\SDBR_RunEndSummary.xml`
- Added `Processes` file references to the main model fragment.
- Added `SDBRRunEndingTime` timer and `SDBRRunSummary` output table.
- Extended `ManufacturingOrdersOutput` states with:
  - `ActualStartTime`
  - `ActualEndTime`
  - `QueueEnteredTime`
  - `QueueWaitMinutes`
  - `WipAfterStart`
  - `WipAfterEnd`
  - `EventStatus`
- Added `ProducedMaterialAddOnProcess=SDBR_MfgEnd` to sched-server `Produce`
  tasks.
- Extended existing sched-server `AssignmentsBeforeProcessing` and
  `AssignmentsAfterProcessing` so operation start/end, queue wait placeholder,
  WIP snapshots and event status are written into `ManufacturingOrdersOutput`.

SDBR parser changes:

- `sdbr/simio_validation.py` now treats `ManufacturingOrdersOutput` and
  `SDBRRunSummary` as explicit Simio result contract tables.
- When `TableStates.sqlite:PlanValues` or `InteractiveValues` contains
  `QueueWaitMinutes`, `WipAfterStart` and `WipAfterEnd`, SDBR maps them into:
  - `QueueMetrics.Status=ParsedFromSDBROutputRows`
  - `WipMetrics.Status=ParsedFromSDBROutputRows`
  - `ScheduleAdherence.Rows[*].ActualStartTime/ActualEndTime/EventStatus`
- If those fields are unavailable, SDBR still falls back to
  `Interactive_Results.stats` and post-run resource logs.

Verification:

- `pytest tests/test_simio_model_template.py tests/test_simio_validation.py -q --basetemp .tmp/pytest-simio-process-chain -p no:cacheprovider`
  returned `13 passed`.
- `python -m compileall -q sdbr` completed successfully.
- Local headless smoke:
  - Generated model:
    `.tmp/simio-process-smoke/RUN-SIMIO/SDBR_Example_RUN-SIMIO.spfx`
  - Result model:
    `.tmp/simio-process-smoke/RUN-SIMIO/SDBR_Example_RUN-SIMIO_result.spfx`
  - `Status=Completed`
  - `FeasibilityConclusion=FeasibleWithWarnings`
  - `QueueMetrics.Status=ParsedFromSDBROutputRows`
  - `WipMetrics.Status=ParsedFromSDBROutputRows`
  - `Throughput.Status=Parsed`, `CompletedOrderCount=1`,
    `UnfinishedOrderCount=0`

Remaining limitations:

- `QueueWaitMinutes` is currently a conservative model-side placeholder from
  the operation output hook. Dedicated input-queue length and true queue wait
  curves still need queue-enter/queue-exit event hooks or Simio report/log
  mapping.
- WIP snapshots are available as start/end evidence per operation. Time-weighted
  WIP curves still need either `Interactive_Results.stats`, StateObservation
  mapping, or explicit model output events.
- Process times still need confirmed unit conversion between APS minutes and
  Simio `UnitType=Time` before using absolute Simio timestamps as final
  business feasibility evidence.

## 2026-06-24 Template Registry And Fixed Source Path

- Added a product-managed Simio template directory:
  `model/templates/simio/`.
- Copied the current SDBR XML template to:
  `model/templates/simio/SDBR_Example_Base.xml`.
- Added the default template identity:
  - `TemplateID`: `SDBR-SIMIO-DBR-V1`
  - `TemplateVersion`: `2026.06.24`
  - `TemplatePath`: `model/templates/simio/SDBR_Example_Base.xml`
  - `TimeUnitPolicy`: APS minutes must be written into Simio time fields with
    explicit `Minutes` units.
- Simio validation now resolves templates from a registry. A validation request
  may provide `TemplateID`; otherwise the active template is used.
- Every generated validation package freezes the template ID, version, source
  path, source type, model name, time-unit policy, Desktop validation status,
  generated model path, and result model path.
- This replaces implicit behavior such as "use the latest generated model" or
  hard-coded transient paths. If no configured template can be resolved, SDBR
  returns a structured template error instead of guessing a model.

## 2026-06-24 Local Full-Speed Headless Rerun

Purpose:

- Re-run the SDBR Simio validation loop with the local headless runner in the
  fastest non-animated `Plan.RunPlan` path.
- Check whether Simio output time and parsed results correspond to the CP-SAT
  schedule used by `RUN-SIMIO`.

Run evidence:

- Source planning run: `RUN-SIMIO`
- Runner mode: `local`
- RLM status: `AlreadyRunning`
- Generated model:
  `.tmp\simio-validation\RUN-SIMIO\SDBR_Example_RUN-SIMIO.spfx`
- Result model:
  `.tmp\simio-validation\RUN-SIMIO\SDBR_Example_RUN-SIMIO_result.spfx`
- Wall-clock elapsed time: about `127.991` seconds
- Helper message: `Simio Plan.RunPlan completed.`
- Selected model: `Model`
- Feasibility conclusion: `FeasibleWithWarnings`

CP-SAT source schedule for this smoke package:

- `TST-WO-100 / TST_WC_DRUM`: `2026-06-23T08:00` to
  `2026-06-23T09:00`, duration `60` minutes.
- `TST-WO-100 / TST_WC_PACK`: `2026-06-23T09:00` to
  `2026-06-23T09:30`, duration `30` minutes.

Parsed Simio output:

- Throughput parsed from
  `Results/Model/TableStates.sqlite:PlanValues`.
- `CompletedOrderCount=1`, `UnfinishedOrderCount=0`.
- Queue evidence parsed from `ManufacturingOrdersOutput.QueueWaitMinutes`.
  Current rows show `0.0` minutes wait for `TST_WC_DRUM` and `TST_WC_PACK`.
- WIP evidence parsed from
  `ManufacturingOrdersOutput.WipAfterStart/WipAfterEnd`.
  Current summary: average WIP `0.5`, max WIP `1.0`.
- Resource utilization parsed from post-run logs:
  - `TST_WC_DRUM`: utilization about `34.2045%`, busy `3612` minutes,
    starved `6948` minutes.
  - `TST_WC_PACK`: utilization about `17.1591%`, busy `1812` minutes,
    starved `8748` minutes.
  - Other template resources had `0%` utilization and were starved during
    scheduled capacity windows.
- `Interactive_Results.stats` was still missing, so result coverage remains
  `PartialResultParsed`.

Conclusion:

- The local full-speed headless runner completes and returns useful throughput,
  queue placeholder, WIP snapshot, resource utilization and adherence rows.
- The output is not yet fully aligned with CP-SAT time. Simio output converted
  the 60-minute and 30-minute CP-SAT operations into multi-day spans
  (`2019-12-02` to `2019-12-11`, then `2019-12-11` to `2019-12-17`).
- The likely cause remains APS-minute to Simio `UnitType=Time` conversion.
  Simio is treating raw duration values as model time units rather than APS
  minutes.
- Therefore this run is valid evidence that the Simio loop can execute and
  return partial metrics, but it is not yet valid evidence that the CP-SAT
  schedule is feasible in Simio with matching operation times.

## 2026-06-24 Minute Units and Auxiliary Task Normalization

Purpose:

- Apply the confirmed Simio time-unit rule: SDBR writes APS durations as
  Simio minute values, and generated `ProcessTime` / `SetupTime` table fields
  must explicitly preserve `Units="Minutes"`.
- Remove template-side auxiliary load/unload task time from validation
  packages so Simio verifies the APS operation duration itself, not extra
  animation or handling time.

Implementation:

- `sdbr/simio_validation.py` now writes `Units="Minutes"` for generated
  `ProcessTime` and `SetupTime` properties.
- Generated routing rows include explicit `SetupTime=0` with minute units.
- During validation-package generation, copied SDBR model payloads normalize
  default `.1 Hours` auxiliary `TaskProcessingTime` rows to `0 Minutes`.
  In this template those two `.1 Hours` rows added 6 minutes before and
  6 minutes after an operation, which explained the observed `+12` minutes.

Validation:

- `pytest tests/test_simio_validation.py -q --basetemp .tmp/pytest-simio-zero-aux -p no:cacheprovider`
  returned `8 passed`.
- `python -m compileall -q sdbr` completed successfully.
- Local full-speed headless validation:
  - Runner mode: `local`
  - RLM status: `AlreadyRunning`
  - Wall-clock elapsed time: about `34.697` seconds
  - `Status=Completed`
  - `FeasibilityConclusion=FeasibleWithWarnings`
  - Result model:
    `.tmp\simio-validation\RUN-SIMIO\SDBR_Example_RUN-SIMIO_result.spfx`

Aligned output:

- CP-SAT source schedule:
  - `TST-WO-100 / TST_WC_DRUM`: `08:00` to `09:00`, `60` minutes.
  - `TST-WO-100 / TST_WC_PACK`: `09:00` to `09:30`, `30` minutes.
- Parsed Simio output:
  - `TST-WO-100 / TST_WC_DRUM`: `08:00` to `09:00`.
  - `TST-WO-100 / TST_WC_PACK`: `09:00` to `09:30`.
  - `CompletedOrderCount=1`, `UnfinishedOrderCount=0`.
  - Queue wait evidence: `0.0` minutes for DRUM and PACK.
  - WIP evidence: average WIP `0.5`, max WIP `1.0`.
  - Resource utilization:
    - `TST_WC_DRUM`: busy `60` minutes, utilization about `0.5682%`.
    - `TST_WC_PACK`: busy `30` minutes, utilization about `0.2841%`.

Conclusion:

- The SDBR Simio headless validation loop now produces operation timestamps
  that match the CP-SAT output for the smoke package.
- Simio default model time can be treated as minutes for this template, but
  XML/table generation must preserve `Units="Minutes"` explicitly for time
  fields to avoid ambiguous interpretation.
- For APS feasibility validation, template auxiliary handling tasks must be
  disabled or included deliberately in CP-SAT. Current V1 disables them in the
  generated validation package.
- The zero-minute auxiliary tasks are intentional V1 validation controls, not
  final model design. They preserve future extension points for a more complete
  ISA-95 style model, such as transfer, queueing, setup, load/unload, labor,
  inspection, maintenance, and material handling. When those elements become
  business requirements, they should be either modeled explicitly in CP-SAT or
  enabled in Simio as simulation-only deltas with clear comparison rules.
- `Interactive_Results.stats` is still not produced, so result coverage remains
  `PartialResultParsed`; however throughput, queue wait evidence, WIP snapshots,
  resource utilization and schedule-adherence rows are available and parsed
  back into SDBR.
