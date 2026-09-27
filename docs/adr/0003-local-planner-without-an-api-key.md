# An Examination still runs when no model key is set

With no API key, the Examination still takes an Observation, writes a Test script from the Controls it found, Runs it, and retries after a Failure. Refusing to run without a key would make the tool-calling path the only path, and the sample Target page could not be examined offline. The model path uses the same observe and write tools; the local planner is the stand-in that calls those tools from the Observation alone.
