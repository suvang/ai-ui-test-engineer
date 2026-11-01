# UI test engineer

Language for examining one page by clicking every call to action on it.

## Language

### The page

**Target page**:
The page at the URL the user asked to examine.
_Avoid_: Site, app, website

**Call to action**:
A visible link or button on the Target page.
_Avoid_: Element, widget, node, selector

**Finding**:
What one call to action did, and whether that click passed.
_Avoid_: Test case, assertion

**API call**:
A fetch or XHR request made because a call to action was clicked.
_Avoid_: Asset, image request

### The examination

**Examination**:
One request to click every call to action on a Target page and report each one.
_Avoid_: Scan, crawl, job

**Report**:
What the user gets back: API calls from opening the page, then every call to action with its navigation result and the API calls that click made.
_Avoid_: Output, log, script
