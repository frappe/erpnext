#!/bin/bash
#
# Audit Python dependencies with pip-audit and report vulnerabilities as a GitHub issue.
#
# Usage:
#   dependency_audit.sh audit <project directory> <markdown report>
#   dependency_audit.sh report <markdown report>
#
set -e

# Writes a markdown report and sets the step output "vulnerable" to true or false. Fails if
# pip-audit fails without finding vulnerabilities.
audit() {
    local project="$1"
    local report="$2"

    pip install pip-audit

    # pip-audit exits with 1 for both vulnerabilities and errors, but writes the report only for vulnerabilities
    if pip-audit --desc on -f markdown -o "$report" "$project"; then
        echo "vulnerable=false" >> "$GITHUB_OUTPUT"
    elif [ -s "$report" ]; then
        echo "vulnerable=true" >> "$GITHUB_OUTPUT"
    else
        exit 1
    fi
}

# Creates "Vulnerable dependencies found on <branch>" if no such issue is open. If one is open,
# comments on it at most once every 15 days, counted from the issue or the last reminder.
# Env: GH_TOKEN, GH_REPO, BRANCH, RUN_URL, NOTIFY (optional mentions)
report() {
    local report="$1"
    local title="Vulnerable dependencies found on $BRANCH"
    local body
    body="$(mktemp)"

    {
        echo "pip-audit found vulnerable dependencies on \`$BRANCH\`."
        echo
        cat "$report"
        echo
        echo "Workflow run: $RUN_URL"
        if [ -n "$NOTIFY" ]; then
            echo
            echo "cc $NOTIFY"
        fi
    } > "$body"

    local issue
    issue=$(gh issue list --state open --label security --search "\"$title\" in:title" --json number,title \
        --jq "map(select(.title == \"$title\")) | first | .number // empty")

    if [ -z "$issue" ]; then
        gh issue create --title "$title" --label security --label dependencies --body-file "$body"
        return
    fi

    local last_notified last_reminder
    last_notified=$(gh api "repos/$GH_REPO/issues/$issue" --jq .created_at)
    last_reminder=$(gh api "repos/$GH_REPO/issues/$issue/comments" --paginate \
        --jq '.[] | select(.user.login == "github-actions[bot]") | .created_at' | tail -n 1)
    last_notified=${last_reminder:-$last_notified}

    if [ "$(date -d "$last_notified" +%s)" -le "$(date -d '15 days ago' +%s)" ]; then
        gh issue comment "$issue" --body-file "$body"
    fi
}

case "$1" in
    audit|report) "$@" ;;
    *) echo "Usage: $0 audit <project directory> <markdown report> | report <markdown report>" >&2; exit 1 ;;
esac
