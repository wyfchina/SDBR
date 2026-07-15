# DDMRP SampleCo Runtime Alignment Design

## Scope

This change aligns the SDBR DDMRP runtime evaluator with the algorithm described in
`nofinish/SampleCowithDemandDrivenMRP.pdf` without moving DDAE-owned parameter
governance into SDBR.

SDBR continues to consume frozen `DLTMinutes`, `TopOfRed`, `TopOfYellow`,
`TopOfGreen`, MOQ, order multiple, profile assignment, and runtime evidence. It does
not calculate or govern ADU, DLT, buffer profiles, variability factors, lead-time
factors, adjustment factors, or decoupling-point placement.

Applicable backend capabilities: `BE-DDMRP-003`, `BE-DDMRP-004`, and
`BE-DDMRP-006`.

## Runtime Rules

### Qualified demand

- Past-due and due-today demand remains qualified.
- When `SpikeQualificationMode = ProvidedByDDSOP`, a row marked
  `QualifiedByDDSOP` is accepted as qualified demand. SDBR must not apply a second
  plain-DLT cutoff to an already governed decision.
- When `SpikeQualificationMode = CalculatedBySDBR`, SDBR requires accepted order
  spike horizon and threshold authority. The current contract does not provide the
  threshold inputs required by the PDF formula, so the runtime adapter must reject
  this mode with a named gate instead of inventing fields or parameters.

### Open supply

- Net flow includes all effective open supply rows in the frozen runtime snapshot.
- Cancelled, closed, completed, and already-received rows remain excluded so
  received quantity is not counted again beside inventory.
- Rows without an expected date remain excluded with a structured warning.
- DLT is not reused as an implicit open-supply cutoff because the PDF does not give
  it that meaning.

### Net flow and replenishment

The existing formulas remain:

```text
Net Flow Position = Qualified On Hand + Qualified Open Supply - Qualified Demand
Suggested Replenishment = Top of Green - Net Flow Position
```

Replenishment is actionable only in Red or Yellow. MOQ and order multiple are
applied after the raw suggestion is calculated.

### Priority metrics

- `PlanningPriorityPercent = NetFlowPosition / TopOfGreen * 100`.
- `ExecutionPriorityPercent = QualifiedOnHandQty / TopOfRed * 100`.
- A zero denominator produces `null`; it must not produce infinity or silently use
  another zone.

### Unit validation

Inventory, demand, open supply, and buffer quantities for one item-location must
use the same UOM. A mismatch rejects runtime evaluation rather than summing
incompatible quantities.

## Contract Boundary

The PDF calculates ADU, DLT, zone sizes, and spike thresholds from detailed profile
parameters. SDBR cannot reproduce those calculations from the current accepted
contract because the required factor values are not present. The implementation
therefore validates and consumes frozen results only. Adding threshold factors or
changing DDAE parameter authority requires a Contract Agent change; no hidden SDBR
fields are allowed.

## Error Handling

- Unsupported SDBR-side spike calculation returns
  `SPIKE_QUALIFICATION_INPUT_INSUFFICIENT`.
- UOM mismatch returns the contract-defined `REFERENCE_NOT_FOUND` code through the
  runtime adapter, with a field-specific message identifying the incompatible UOM;
  the standalone evaluator raises the same deterministic validation message.
- Missing supply dates remain warnings and do not stop other item-location rows.

## Test Strategy

Tests must prove:

1. A DDS&OP-qualified future spike beyond plain DLT is included.
2. Effective open supply beyond DLT is included.
3. Incompatible demand or supply UOM is rejected.
4. Planning and execution priority percentages match the PDF formulas.
5. `CalculatedBySDBR` remains blocked without accepted threshold authority.
6. Existing Red/Yellow replenishment and Green/AboveGreen monitor behavior does not
   regress.
