#!/usr/bin/env bash
# Format evidence links from stdin or arguments
# Usage: echo "src/auth/jwt.ts:42-67 :: generateAccessToken" | ./format-evidence.sh
# Output: [E] src/auth/jwt.ts:42-67 :: generateAccessToken()

while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip empty lines and already-formatted lines
  if [[ -z "$line" ]]; then continue; fi
  if [[ "$line" == \[E\]* ]] || [[ "$line" == \[Unknown\]* ]] || [[ "$line" == \[Stale* ]] || [[ "$line" == \[Deprecated\]* ]]; then
    echo "$line"
    continue
  fi
  # Format as evidence link
  echo "[E] $line"
done
