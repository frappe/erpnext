#!/bin/bash

set -e

source "$(dirname "${BASH_SOURCE[0]}")/git-auth.sh"

githubbranch=${GITHUB_BASE_REF:-${GITHUB_REF##*/}}
frappeuser=${FRAPPE_USER:-"frappe"}
frappecommitish=${FRAPPE_BRANCH:-}

# A stacked pull request targets another erpnext branch, which has no counterpart in frappe.
# Fall back to develop so the bench is still installed. An explicit FRAPPE_BRANCH is trusted as
# given, since it can be a commit sha rather than a branch.
if [ -z "$frappecommitish" ]; then
    frappecommitish=$githubbranch

    # git ls-remote --exit-code reports 2 for a branch that is not there and 128 for a remote it
    # could not reach. Only the first one is proof of absence; keep the branch on anything else so
    # a flaky probe cannot install an unrelated frappe.
    probe=0
    git ls-remote --exit-code --heads "https://github.com/${frappeuser}/frappe" "$frappecommitish" >/dev/null 2>&1 || probe=$?

    if [ "$probe" -eq 2 ]; then
        echo "frappe has no branch ${frappecommitish}, falling back to develop" >&2
        frappecommitish=develop
    elif [ "$probe" -ne 0 ]; then
        echo "could not reach frappe to check for branch ${frappecommitish} (git ls-remote exited ${probe}), keeping it" >&2
    fi
fi

echo "$frappecommitish"
