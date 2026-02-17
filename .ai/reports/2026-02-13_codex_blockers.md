# Codex Blockers - 2026-02-13

## Task BS-002 (Docker multi-stage)
- Affected task: `P2-3 / BS-002 / Docker multi-stage`
- Status: `STOPPED (failed benchmark validation twice, no commit created)`

### Attempt 1
- Command:
  - `docker build -t prometheus-api:perf-ms ./prometheus-api`
- Error output:
  - `docker : The term 'docker' is not recognized as the name of a cmdlet, function, script file, or operable program.`
- Minimal fix:
  - Switched to Docker CLI absolute path.

### Attempt 2
- Command:
  - `C:\Program Files\Docker\Docker\resources\bin\docker.exe build -t prometheus-api:perf-ms ./prometheus-api`
- Error output:
  - `error getting credentials - err: exec: "docker-credential-desktop": executable file not found in %PATH%`
  - `failed to solve: error getting credentials`
- Suspected cause:
  - Docker credential helper (`docker-credential-desktop`) is not resolvable from current PATH/session, so Docker cannot pull base image metadata.

### Rollback/State
- Reverted local task change (`prometheus-api/Dockerfile`) via `git restore`.
- No BS-002 commit was created.
