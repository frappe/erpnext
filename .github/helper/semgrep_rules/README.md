# Semgrep linting

## What is semgrep?
Semgrep or "semantic grep" is language agnostic static analysis tool. In simple terms semgrep is syntax-aware `grep`, so unlike regex it doesn't get confused by different ways of writing same thing or whitespaces or code split in multiple lines etc.

Example:

To check if a translate function is using f-string or not the regex would be `r"_\(\s*f[\"']"` while equivalent rule in semgrep would be `_(f"...")`. As semgrep knows grammer of language it takes care of unnecessary whitespace, type of quotation marks etc.

You can read more such examples in `.github/helper/semgrep_rules` directory.

# Why/when to use this?
We want to maintain quality of contributions, at the same time remembering all the good practices can be pain to deal with while evaluating contributions. Using semgrep if you can translate "best practice" into a rule then it can automate the task for us.

## Running locally

Install semgrep using homebrew `brew install semgrep` or pip `pip install semgrep`.

To run locally use following command:

`semgrep --config=.github/helper/semgrep_rules [file/folder names]`

## Testing
semgrep allows testing the tests. Refer to this page: https://semgrep.dev/docs/writing-rules/testing-rules/

When writing new rules you should write few positive and few negative cases as shown in the guide and current tests.

To run current tests: `semgrep --test --test-ignore-todo .github/helper/semgrep_rules`


## Reference

If you are new to Semgrep read following pages to get started on writing/modifying rules:

- https://semgrep.dev/docs/getting-started/
- https://semgrep.dev/docs/writing-rules/rule-syntax
- https://semgrep.dev/docs/writing-rules/pattern-examples/
- https://semgrep.dev/docs/writing-rules/rule-ideas/#common-use-cases
