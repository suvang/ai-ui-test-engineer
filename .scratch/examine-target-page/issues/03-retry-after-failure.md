# 03: A Failure is kept and another Attempt is made

Status: done

**What to build:** When the first Test script fails, the Examination writes another one. The Report keeps the Failure. A later pass makes the Report a pass. The Examination stops after three failing Attempts.

**Blocked by:** 01

## Parent

`.scratch/examine-target-page/spec.md`

## What to build

A failed Run is not the end of the Examination. The user can see the Failure and, when a later Attempt passes, a passing Report. Three failures end the Examination as a fail.

## Acceptance criteria

- [ ] The first Attempt can fail and a later Attempt can pass
- [ ] The Report keeps the Failure text from the first Attempt
- [ ] A passing later Attempt makes the Report a pass
- [ ] Three failing Attempts stop the Examination, and the Report did not pass

## Blocked by

- 01: A passing Test script for a Button and a Form field

## Comments
