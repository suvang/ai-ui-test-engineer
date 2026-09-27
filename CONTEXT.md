# UI test engineer

Language for examining one Target page and proving that examination with a Test script.

## Language

### The page

**Target page**:
The page at the URL the user asked to examine.
_Avoid_: Site, app, website

**Control**:
A Button, Form field, or Navigation link on a page.
_Avoid_: Element, widget, node, selector

**Button**:
A Control that can be pressed.
_Avoid_: Click target, action

**Form field**:
A Control the user can type into.
_Avoid_: Input, textbox, widget

**Navigation link**:
A Control that moves to another page on the same origin.
_Avoid_: Anchor, href, menu item

**Flow**:
The step from the Target page along one Navigation link to the next page.
_Avoid_: Crawl, journey, path

**Observation**:
The words, Controls, and picture captured from a page.
_Avoid_: DOM, HTML dump, scrape

### The examination

**Examination**:
One request to understand a Target page and prove it with a Test script.
_Avoid_: Scan, audit, job

**Test script**:
The executable Playwright test an Examination writes for a Target page.
_Avoid_: Spec file, Cypress test, suite

**Run**:
Executing a Test script against the Target page.
_Avoid_: Build, job

**Attempt**:
One cycle of writing a Test script and Running it.
_Avoid_: Retry, iteration

**Failure**:
The reason a Run did not pass.
_Avoid_: Error, exception, flake

**Report**:
What the user gets back from an Examination: the Controls, the Test script, and every Attempt.
_Avoid_: Output, log, result
