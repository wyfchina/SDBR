# Backend Readiness Checkpoint

Date: 2026-06-19

## Scope

This checkpoint covers the planner backend before formal UI development:

- frozen master-data and operational-state inputs
- Gurobi planning runs
- persistent worker queue and leases
- retry, dead-letter, recovery, RBAC, and audit
- concurrency, performance, backup, and recovery verification

## Verified Behaviors

- A Planning Run keeps immutable references to its Master Data Version and
  Operational State Snapshot.
- Gurobi execution supports a configured time limit and structured diagnostics.
- Worker leases survive application restarts and expired leases can be recovered.
- Lease tokens are returned only when claimed; persistent state stores hashes.
- Retryable failures are delayed and eventually enter `DeadLetter`.
- Dead-lettered runs can be manually recovered without replacing frozen inputs.
- RBAC can be enabled for Viewer, Planner, Worker, and Admin roles.
- Audit events persist with SQLite state and are restored from backup.
- Two workers in one API process cannot claim the same queued run.
- Two API instances sharing SQLite allow only one claim to persist; the other
  receives a state revision conflict.
- Corrupt primary SQLite state restores Planning Runs and audit events from the
  backup database.

## Performance Baseline

Test data: 1,000 Planning Runs, 500 matching the list filter.

Operation: paginated status-filtered list plus queue metrics aggregation.

- iterations: 20
- minimum: 58.90 ms
- median: 79.84 ms
- maximum: 404.97 ms
- acceptance baseline: under 2,000 ms

This is an in-process API baseline, not a production network or database load
test.

## Deployment Boundaries

- SQLite is suitable for the current single-service development deployment.
  Cross-instance conflicts are detected and returned as HTTP 409; a future
  multi-node deployment should use row-level transactional storage.
- The installed Gurobi license is restricted to non-production use and expires
  on 2026-11-23.
- The worker is available as an independent process but is not automatically
  installed as a Windows service.
- Authentication enforcement is configurable. The current local workbench runs
  in development mode because no login UI or identity provider is connected.
- OR-Tools and Simio remain paused by project decision.

## UI Checkpoint

The backend business objects and lifecycle contracts are now sufficiently stable
to begin formal planner UI design. UI work should consume the version, snapshot,
Planning Run, queue metrics, audit, and recovery APIs rather than expose raw JSON
master-data payloads.
