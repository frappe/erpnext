# frappe-pr-bot

frappe-pr-bot reviews pull requests in this repo the way a maintainer does. It reads the change, checks the root cause and the other places the same code runs, and for UI, data or bigger changes it checks the PR out on a real bench and reproduces it, in a browser when there is a UI. It posts one review, never approves and never merges.

## Ask for a review

Write a comment on the pull request:

| Comment | What it does |
|---|---|
| `@frappe-pr-bot review` | Reviews the change. Switches to a deep review by itself for UI, data or large changes |
| `@frappe-pr-bot deep review` | Checks the PR out on a bench and reproduces the bug or the feature |
| `@frappe-pr-bot full review` | Reviews from scratch, even if this commit was reviewed before. `full deep review` works too |
| `@frappe-pr-bot help` | Shows these commands |

Other ways to get a review:
- Re-request a review from frappe-pr-bot with the reviewers button. It reviews again in the mode it used last.
- The `deep-review` label makes every review of the PR a deep one, unless someone asks for a normal review.

## Ask in your own words

After `@frappe-pr-bot` you can write anything, in your own words:
- `@frappe-pr-bot is this safe to merge?`
- `@frappe-pr-bot can you share a screenshot of your test?`
- `@frappe-pr-bot deep review check it on a site with two companies`

Text after a command is passed to the review as an extra instruction.

## Question a finding

If you are the PR author or a maintainer, reply in any of the bot's review threads, no mention needed. For example: "how can I reproduce this?" or "I think this is already handled in validate". The bot runs it on the bench, on develop and on your branch, and replies with the steps and what it saw. If the finding turns out to be wrong, it says so and resolves the thread.

## What to expect

- A 👀 reaction when your request is picked up, then 👍 when the review is posted, or 😕 if it could not finish.
- A review takes a few minutes, a deep review up to about twenty.
- It requests changes only for problems in the code. Asks about the description or screenshots come as comments.
