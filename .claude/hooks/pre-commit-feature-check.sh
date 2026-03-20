#!/bin/bash
# PreToolUse hook: block "feat:" commits when new backend endpoints lack frontend coverage
cd "c:/Users/zmuda/google ads helper v1"

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)

# Only intercept Bash calls
if [ "$TOOL" != "Bash" ]; then
  echo '{}'; exit 0
fi

CMD=$(echo "$INPUT" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

# Only trigger on git commit with feat: prefix
if ! echo "$CMD" | grep -qE 'git commit'; then
  echo '{}'; exit 0
fi

# Extract commit message from command
MSG=$(echo "$CMD" | grep -oP "(?<=feat:)[^'\"]*" 2>/dev/null || true)
if [ -z "$MSG" ]; then
  # Not a feat: commit — allow
  echo '{}'; exit 0
fi

# Find new endpoints in staged backend router files
NEW_ENDPOINTS=$(git diff --cached --unified=0 -- 'backend/app/routers/*.py' 2>/dev/null \
  | grep -E '^\+.*@router\.(get|post|put|patch|delete)\(' \
  | grep -oP '(?<=@router\.(get|post|put|patch|delete)\()["\x27]/[^"\x27]+' \
  | tr -d '"\x27' \
  | sort -u)

if [ -z "$NEW_ENDPOINTS" ]; then
  # No new endpoints in this commit — allow
  echo '{}'; exit 0
fi

# Check each endpoint for frontend usage
MISSING=""
for EP in $NEW_ENDPOINTS; do
  # Strip leading / and build search pattern
  EP_CLEAN=$(echo "$EP" | sed 's|^/||')

  # Search frontend for API calls matching this endpoint path
  FOUND=$(grep -rl "$EP_CLEAN" frontend/src/ 2>/dev/null | head -1)

  if [ -z "$FOUND" ]; then
    MISSING="${MISSING}\n  - ${EP}"
  fi
done

if [ -n "$MISSING" ]; then
  cat <<EOF
{"decision":"block","reason":"FEATURE CHECK: feat: commit zawiera nowe endpointy BEZ frontend coverage:${MISSING}\n\nDodaj wywolania API w frontend lub uzyj innego prefixu (np. 'backend:' / 'api:') jesli to swiadomy backend-only commit."}
EOF
  exit 0
fi

echo '{}'
