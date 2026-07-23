#!/bin/bash
# Stop hook: copy this session's transcript into transcripts/, named by session id.
# Hook input (JSON on stdin) includes session_id and transcript_path.
set -euo pipefail

input=$(cat)
session_id=$(echo "$input" | jq -r '.session_id')
transcript_path=$(echo "$input" | jq -r '.transcript_path')

repo_dir=$(cd "$(dirname "$0")/../.." && pwd)

if [[ -n "$session_id" && "$session_id" != "null" && -f "$transcript_path" ]]; then
  cp "$transcript_path" "$repo_dir/transcripts/${session_id}.jsonl"
fi
