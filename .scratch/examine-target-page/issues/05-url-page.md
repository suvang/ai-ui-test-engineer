# 05: The page takes a URL and shows the Report

Status: done

**What to build:** The local page accepts a URL, runs an Examination, and shows the Controls, the Test script, and each Attempt. An empty URL is rejected. A non-http URL fails the Examination. The sample Target page is offered from the page.

**Blocked by:** 01, 02, 03, 04

## Parent

`.scratch/examine-target-page/spec.md`

## What to build

A person can open the local page, examine a URL, and read the Report there. The sample Target page is one of the URLs they can submit.

## Acceptance criteria

- [ ] Posting the sample URL returns a passing Report with the Test script and the Controls
- [ ] An empty URL is rejected
- [ ] A non-http URL returns a Report that did not pass and did not pretend to
- [ ] The page offers the sample Target page and renders the Report fields

## Blocked by

- 01: A passing Test script for a Button and a Form field
- 02: The Test script follows one Flow
- 03: A Failure is kept and another Attempt is made
- 04: The model observes before it writes

## Comments
