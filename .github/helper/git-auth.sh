#!/bin/bash

# Authenticate git against github.com with the job token: anonymous git-over-HTTPS from the
# runners gets throttled to a 401, which kills whichever clone is in flight — the frappe probe
# or fetch, or payments under `bench get-app`.
#
# A credential helper rather than a url.insteadOf rewrite, because `git clone` PERSISTS a
# rewritten URL into the new repo's .git/config: an insteadOf would leave the token sitting in
# apps/payments/.git/config on the runner. A helper is consulted only when github.com actually
# challenges, and leaves the stored remote URL untouched. Passing it through GIT_CONFIG_* keeps
# the token out of ~/.gitconfig too, and child processes inherit it (bench shells out to git).
ci_github_token=${CI_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}
if [ -n "$ci_github_token" ]; then
    export CI_GITHUB_TOKEN="$ci_github_token"
    export GIT_CONFIG_COUNT=3
    # Reset first: git runs EVERY configured helper and calls `store` on them after a successful
    # auth, so a `credential.helper=store` inherited from the image's gitconfig would write the
    # token to ~/.git-credentials. An empty value clears the list before ours is added.
    export GIT_CONFIG_KEY_0="credential.helper"
    export GIT_CONFIG_VALUE_0=""
    export GIT_CONFIG_KEY_1="credential.https://github.com.username"
    export GIT_CONFIG_VALUE_1="x-access-token"
    export GIT_CONFIG_KEY_2="credential.https://github.com.helper"
    # Single-quoted: $CI_GITHUB_TOKEN is expanded by the shell git runs the helper in, so the
    # token is read from the environment at call time and never stored anywhere. Answering only
    # `get` makes the helper inert for git's `store`/`erase` calls.
    export GIT_CONFIG_VALUE_2='!f() { test "$1" = get && echo "password=$CI_GITHUB_TOKEN"; }; f'
fi

# Whatever happens, never sit on a credential prompt: fail fast and legibly instead.
export GIT_TERMINAL_PROMPT=0
