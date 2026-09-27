# 04: The model observes before it writes

Status: done

**What to build:** A model session must call observe, and the tool result includes the page's words and a picture, before write_test. The Test script that write_test returns is what the Report Runs.

**Blocked by:** 01

## Parent

`.scratch/examine-target-page/spec.md`

## What to build

The model path is tool calling. The Observation the model receives contains the heading and a non-empty picture. The Report's Test script is the one the model wrote, and the Run of that script is the Report's outcome.

## Acceptance criteria

- [ ] The first tool call is observe
- [ ] The observe result includes the sample heading and a picture larger than an empty file
- [ ] The Report's Test script is the source the model passed to write_test
- [ ] The Run of that script passed

## Blocked by

- 01: A passing Test script for a Button and a Form field

## Comments
