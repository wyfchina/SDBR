# Release Deviation Stability Design

## Goal

Monitor the difference between the Gurobi-derived rope release time and the
actual release time without allowing small execution noise to cause repeated
rescheduling.

## Boundary

The scheduling engine remains responsible for protected due dates and planned
rope release metadata. The release gate remains responsible for material, WIP,
and timing checks. This feature sits between them as a pure decision policy. It
does not change Gurobi constraints and does not implement OR-Tools or Simio.

## Policy

For each order, calculate signed deviation minutes as actual release time minus
planned rope release time. Positive values are late; negative values are early.

The policy returns one of three actions:

- `Monitor`: deviation is within the configurable tolerance.
- `Review`: deviation exceeds tolerance but has not met the stability trigger.
- `Replan`: deviation exceeds the replan threshold, or repeated material/WIP
  blocking reaches the configured consecutive-event threshold, and the replan
  cooldown has elapsed.

The default policy uses a 30-minute tolerance, a 120-minute replan threshold,
three consecutive blocked evaluations, and a 60-minute replan cooldown. All
values are configurable and validated.

## Data Contract

Input contains order ID, planned release time, evaluated actual release time,
whether the gate allowed release, consecutive blocked count, and optional last
replan time. Output contains signed and absolute deviation, timing status,
severity, action, replan flag, and a stable reason code.

## Error Handling

Reject negative thresholds, a replan threshold smaller than tolerance, a
blocked-event threshold below one, a negative blocked count, and timezone-aware
versus timezone-naive datetime mixtures.

## Testing

Unit tests cover tolerance monitoring, delayed review, threshold replan,
repeated gate blocking, cooldown suppression, and invalid policy values. The
full existing suite remains the regression gate.
