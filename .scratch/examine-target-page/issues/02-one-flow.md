# 02: The Test script follows one Flow

Status: done

**What to build:** The Report for the sample Target page includes one Navigation link, Shipping, and the Test script clicks it and checks the next page. The cross-origin link is not in the Test script.

**Blocked by:** 01

## Parent

`.scratch/examine-target-page/spec.md`

## What to build

Examining the sample Target page records a single Flow and the passing Test script walks it. A link that leaves the origin is not activated.

## Acceptance criteria

- [ ] The Report lists a Navigation link named Shipping
- [ ] The Test script clicks Shipping and checks the next heading
- [ ] The Test script does not mention the cross-origin host
- [ ] The Run passed

## Blocked by

- 01: A passing Test script for a Button and a Form field

## Comments
