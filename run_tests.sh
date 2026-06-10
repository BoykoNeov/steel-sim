#!/usr/bin/env sh
# Test runner. Args pass through to pytest, so the tiered gate (ADR 0003) is one flag away:
#   ./run_tests.sh -m "not slow"    # routine fast lane (the always-on suite)
#   ./run_tests.sh                  # full suite — adds the slow live-CALPHAD + notebook tests (CI / release)
#   ./run_tests.sh steel            # scope to the simulator
exec python -m pytest "$@"
