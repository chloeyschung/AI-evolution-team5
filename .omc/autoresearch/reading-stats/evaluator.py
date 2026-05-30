#!/usr/bin/env python3
"""Evaluator for reading-stats mission."""
import json
import os
import subprocess
import sys

results = {}

# Check 1: stats router file exists
stats_file = "src/api/routers/stats.py"
results["file_exists"] = os.path.exists(stats_file)

# Check 2: endpoint defined
if results["file_exists"]:
    content = open(stats_file).read()
    results["has_get_route"] = '@router.get("/swipe-stats"' in content or "@router.get('/stats'" in content
    results["has_kept"] = "kept" in content
    results["has_deleted"] = "deleted" in content
    results["has_skipped"] = "skipped" in content
else:
    results["has_get_route"] = False
    results["has_kept"] = False
    results["has_deleted"] = False
    results["has_skipped"] = False

# Check 3: test file exists
test_file = "tests/api/test_stats.py"
results["test_file_exists"] = os.path.exists(test_file)

# Check 4: run tests if file exists
if results["test_file_exists"]:
    proc = subprocess.run(
        [".venv/bin/pytest", test_file, "--tb=short", "-q"],
        capture_output=True, text=True
    )
    results["tests_pass"] = proc.returncode == 0
    results["test_output"] = proc.stdout[-500:] + proc.stderr[-200:]
else:
    results["tests_pass"] = False
    results["test_output"] = "test file not found"

# Score
checks = [results["file_exists"], results["has_get_route"],
          results["has_kept"], results["has_deleted"], results["has_skipped"],
          results["test_file_exists"], results["tests_pass"]]
score = sum(checks) / len(checks)
passed = score >= 1.0

output = {"pass": passed, "score": round(score, 2), "details": results}
print(json.dumps(output, indent=2))
