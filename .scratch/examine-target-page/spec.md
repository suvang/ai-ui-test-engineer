# Examine a Target page

Status: done

## Problem Statement

Writing UI tests by hand is slow, and a person has to already know the Buttons, Form fields, and Navigation links on a page before they can write anything. The user wants to hand over a URL and get back an executable Test script that was actually Run, plus a Report when it fails.

## Solution

The user enters the URL of a Target page. An Examination opens that page, records an Observation (the words and Controls, and a picture of the page), and writes a Python Playwright Test script. It Runs the Test script. When the Run fails, it makes another Attempt, up to three, and the Report keeps every Failure. With an API key, a model calls tools to take the Observation and to write the Test script, and it sees the picture. Without a key, a local planner calls the same tools from the Observation alone.

## User Stories

1. As a person examining a page, I want to enter a URL, so that an Examination starts on that Target page.
2. As a person examining a page, I want a Report when the Examination finishes, so that I can see what was found and whether the Test script passed.
3. As a person examining a page, I want the Report to include the Test script, so that I can read and run it myself.
4. As a person examining a page, I want the Test script to be a complete Python Playwright file, so that I can run it again without the agent.
5. As a person examining a page, I want each Button on the Target page named in the Report, so that I can see what can be pressed.
6. As a person examining a page, I want the Test script to check that a Button is visible, so that the proof matches the page.
7. As a person examining a page, I want the Test script not to press a Button, so that the Examination does not change the Target page.
8. As a person examining a page, I want each Form field named in the Report, so that I can see what can be typed into.
9. As a person examining a page, I want the Test script to fill a Form field and check the value, so that the field is shown to accept text.
10. As a person examining a page, I want the Test script not to submit a Form field, so that the Examination does not send data to the Target page.
11. As a person examining a page, I want one same-origin Navigation link recorded as a Flow, so that the Test script covers leaving the Target page once.
12. As a person examining a page, I want the Test script to click that Navigation link and check the next page's heading, so that the Flow is executed, not only listed.
13. As a person examining a page, I want a cross-origin link left out of the Test script, so that the Examination does not leave the origin.
14. As a person examining a page, I want the Observation to include the words on the page, so that the Test script is grounded in what was visible.
15. As a person examining a page, I want the Observation to include a picture of the page, so that a model can see the page and not only its words.
16. As a person examining a page, I want a failed Run to be followed by another Attempt, so that a bad Test script can be replaced.
17. As a person examining a page, I want every Attempt and its Failure kept in the Report, so that I can see what was tried.
18. As a person examining a page, I want the Examination to stop after three Attempts, so that a page that cannot pass does not loop.
19. As a person examining a page, I want a passing later Attempt to make the Report a pass, so that the last Run is the outcome.
20. As a person examining a page, I want an Examination with no API key to still write and Run a Test script, so that the sample page works offline.
21. As a person examining a page, I want a model to call a tool for the Observation before it writes a Test script, so that the script comes from the page and not from a guess.
22. As a person examining a page, I want the picture included when the model is shown the Observation, so that the model can use it on the next Attempt.
23. As a person examining a page, I want a model to write a new Test script after a Failure, so that the Failure is an input to the next Attempt.
24. As a person examining a page, I want an empty URL rejected, so that an Examination is not started with nothing to open.
25. As a person examining a page, I want a URL that is not http or https to fail the Examination, so that other schemes are not treated as a Target page.
26. As a person examining a page, I want a Target page that cannot be opened to fail the Examination with that reason, so that the Report does not claim a pass.
27. As a person examining a page, I want the page to show the Controls, the Test script, and each Attempt, so that I can read the Report without the terminal.
28. As a person examining a page, I want the sample Target page offered on the page, so that I can try an Examination without choosing an external URL.

## Implementation Decisions

- The module interface is `TestEngineer.examine(url) -> Examination`. Callers learn the URL and the Report. Exploration, script writing, the Run, and the retry loop sit behind that interface.
- An Examination accepts only an `http` or `https` URL. Anything else returns a Report that did not pass, and does not open a browser.
- One Observation records the page heading, the accessible words, a picture, and up to eight Controls: Buttons, Form fields, and at most one Navigation link. The Navigation link is same-origin and is not the Target page itself. Its destination heading is read by opening that link during the Observation, then returning to the Target page for the picture.
- The Test script asserts the heading, asserts each Button is visible, fills each Form field with `2` and asserts that value, and clicks the Navigation link once before asserting the destination heading. It does not press Buttons and does not submit.
- Writing and Running share one loop of at most three Attempts. A passing Run ends the loop. The Report's outcome is the last Attempt.
- Both planners speak the same tools: `observe` and `write_test`. The local planner calls `observe`, then `write_test` from the Observation. After a Failure whose text names a Control, the next Test script omits that Control. The OpenAI planner is used only when `OPENAI_API_KEY` is set. Its tool result for `observe` includes the picture, sent to the model as an image as well as the words.
- The page is a caller of `examine`. It posts the URL and renders the Report. The sample Target page is a desk page with a Button, a Form field, a same-origin Navigation link, and a cross-origin link.

## Testing Decisions

- The seam is `TestEngineer.examine(url) -> Examination`. Tests call that method. They do not read private helpers.
- A good test describes what a person can see in the Report: which Controls were found, what the Test script promises, and whether the Run passed. Expected Controls and headings come from the sample Target page, which is a fixed page the test serves, not from recomputing the explorer.
- The route is the same module: one test posts a URL through the page's endpoint and reads the same Report fields.
- The model path is tested with a scripted tool session, not a live API key. The session's tool results are the test's own adapter, so the test may read the Observation payload that adapter received.
- There is no prior test suite in this project. The sibling projects test through the module a caller uses, and this seam follows that.

## Out of Scope

- Logging in, cookies supplied by the user, and pages behind a password.
- Pressing Buttons, submitting forms, file uploads, and any action that would change the Target page.
- More than one Flow, cross-origin navigation, and crawling an entire site.
- Cypress, TypeScript Playwright, and visual pixel diffs.
- Hosting, a queue of Examinations, and more than one Examination at a time.

## Further Notes

The approved plan fixed the starting point: Python 3.11, a small local page, Playwright for the Observation and the Test script, and an OpenAI tool-calling loop that still Runs when no API key is set. ADRs 0001, 0002, and 0003 record the choices that would be costly to reverse.
