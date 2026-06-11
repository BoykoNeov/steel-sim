#!/usr/bin/env pwsh
# Test runner. Args pass through to pytest, so the tiered gate (ADR 0003) is one flag away:
#   ./run_tests.ps1 -m "not slow"    # routine fast lane (the always-on suite)
#   ./run_tests.ps1                  # full suite — adds the slow live-CALPHAD + notebook tests (CI / release)
#   ./run_tests.ps1 steel            # scope to the simulator
#   ./run_tests.ps1 -k erfc          # filter by name
#   ./run_tests.ps1 -n0              # force serial (overrides the default `-n auto`)
# Runs in parallel by default — `addopts` sets `-n auto --dist loadgroup` (pytest-xdist, in
# the [test] extra). Pass `-n0` for a clean serial traceback when debugging a single test.
$ErrorActionPreference = "Stop"
python -m pytest @args
exit $LASTEXITCODE
