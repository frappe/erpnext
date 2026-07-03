#!/usr/bin/env python3
# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import subprocess
import sys
import tempfile
from pathlib import Path


RULES_REPO = "https://github.com/frappe/semgrep-rules.git"


def run(command, **kwargs):
	return subprocess.run(command, check=True, **kwargs)


def get_rules_repo_default_branch():
	result = subprocess.run(
		["git", "ls-remote", "--symref", RULES_REPO, "HEAD"],
		check=True,
		stdout=subprocess.PIPE,
		text=True,
	)
	for line in result.stdout.splitlines():
		if line.startswith("ref: refs/heads/"):
			return line.split()[1].removeprefix("refs/heads/")

	return "master"


def get_frappe_rules_dir():
	rules_dir = Path(tempfile.gettempdir()) / "frappe-semgrep-rules"
	default_branch = get_rules_repo_default_branch()
	if rules_dir.exists():
		run(["git", "-C", str(rules_dir), "fetch", "--depth", "1", "origin", default_branch])
		run(["git", "-C", str(rules_dir), "reset", "--hard", f"origin/{default_branch}"])
	else:
		run(["git", "clone", "--depth", "1", "--branch", default_branch, RULES_REPO, str(rules_dir)])

	return rules_dir / "rules"


def get_baseline_commit():
	for ref in ("origin/develop", "develop"):
		result = subprocess.run(
			["git", "rev-parse", "--verify", "--quiet", ref],
			check=False,
			stdout=subprocess.DEVNULL,
		)
		if result.returncode == 0:
			return ref


def run_semgrep(configs, includes=None):
	command = ["semgrep", "scan", "--error", "--metrics=off", "--disable-version-check"]
	baseline_commit = get_baseline_commit()
	if baseline_commit:
		command.extend(["--baseline-commit", baseline_commit])

	for config in configs:
		command.extend(["--config", str(config)])

	for include in includes or []:
		command.extend(["--include", include])

	return run(command)


def main():
	rules_dir = get_frappe_rules_dir()
	run_semgrep([rules_dir, "r/python.lang.correctness"])
	run_semgrep(["semgrep/test-correctness.yml"], includes=["**/test_*.py"])


if __name__ == "__main__":
	sys.exit(main())
