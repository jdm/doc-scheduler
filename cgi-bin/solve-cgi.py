#!/usr/bin/env python3
import cgi
import sys
import os
import json
import urllib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import solve

print("Content-Type: application/json")
print()

body = sys.stdin.read(int(os.environ["CONTENT_LENGTH"]))
query = os.environ["QUERY_STRING"]
pairs = urllib.parse.parse_qs(query)
inputs = solve.process_inputs(body)
docs, desired, preferred, unavailable = inputs
num_days = int(pairs["days"][0])
result = solve.solve_shift_scheduling(docs, desired, preferred, unavailable, solve.MAX_UNFILLED, num_days)
print(json.dumps(result))
