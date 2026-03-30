Use uv. Use uv run. Don't pollute system python when a library is "missing"

Consult Makefile and Justfile. If *-llm commands exist consider using them because they are token efficient (not verbose)

If you do run commands directly, make output token efficient unless you're looking for a particular problem.

You may or may not be stuck in a Powershell sandbox (If you are Gemini or Codex or Copilot). The user is on Windows with
git-bash, and is not eager to switch over to Powershell just because you are in a powershell sandbox.

The build scrips must succeed in Github Actions which run in mac, linux and windows.