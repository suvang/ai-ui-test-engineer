# Test scripts are Python Playwright

The Examination writes and Runs a Python Playwright Test script, in the same language as the agent. A TypeScript Playwright suite or a Cypress suite would need a second runtime to execute, and the Failure from that runtime would be a worse input to the next Attempt. Python Playwright keeps the write, the Run, and the retry on one machine.
