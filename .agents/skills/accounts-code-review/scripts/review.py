#!/usr/bin/env python3
"""Deterministic driver for accounts-code-review.

    review.py init     --workdir W --pr N --requirement REF --site S --bench B
    review.py analyze  --workdir W
    review.py lock     --workdir W [--reason TEXT]
    review.py run      --workdir W [--keep-data]
    review.py report   --workdir W
    review.py restore  --workdir W
    review.py cleanup  --workdir W [--run N]

`run` deletes everything it created on the site when it ends, unless --keep-data
is given. `cleanup` deletes a kept run's data later.

Only the standard library. The agent writes requirement.md, code-review.md,
s0.py and expect.json; this script does everything else, in a fixed order.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# After `init`, every command runs from the snapshot in <workdir>/scripts (see main):
# the review switches the app checkout, which may not contain this skill, and a
# skill update must not change a review between its lock and its run.
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
LOCKED_FILES = ("plan.json", "s0.py", "expect.json", "ui.spec.mjs")
PLAYWRIGHT = "1.49.1"  # pinned: a browser upgrade must not change a verdict
GIT_ENV = {
	"GIT_AUTHOR_NAME": "review",
	"GIT_AUTHOR_EMAIL": "review@localhost",
	"GIT_COMMITTER_NAME": "review",
	"GIT_COMMITTER_EMAIL": "review@localhost",
	"GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
	"GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
}


class Failure(Exception):
	pass


# ---------------------------------------------------------------- helpers


def sh(*cmd, cwd=None, env=None, check=True):
	result = subprocess.run(
		[str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})}
	)
	if check and result.returncode:
		raise Failure(f"{' '.join(map(str, cmd))} failed:\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}")
	return result.stdout.strip()


def read(path):
	return json.loads(Path(path).read_text())


def write(path, data):
	Path(path).parent.mkdir(parents=True, exist_ok=True)
	Path(path).write_text(json.dumps(data, indent=1, sort_keys=True, default=str) + "\n")


def file_hashes(workdir):
	out = {}
	for name in LOCKED_FILES:
		path = Path(workdir, name)
		out[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
	digest = hashlib.sha256()
	for path in sorted(Path(workdir, "scripts").rglob("*")):
		if path.is_file() and "__pycache__" not in path.parts:
			digest.update(str(path.relative_to(workdir)).encode() + b"\0" + path.read_bytes())
	out["scripts"] = digest.hexdigest()
	return out


class Review:
	def __init__(self, workdir):
		self.workdir = Path(workdir).resolve()
		self.state_path = self.workdir / "state.json"
		self.state = read(self.state_path) if self.state_path.exists() else {}

	@property
	def app_dir(self):
		return Path(self.state["bench"], "apps", self.state["app"])

	def git(self, *args, env=None, check=True):
		return sh("git", "-C", self.app_dir, *args, env=env, check=check)

	# ------------------------------------------------------------ init

	def init(self, pr, requirement, site, bench, repo, app, bench_cmd):
		self.workdir.mkdir(parents=True, exist_ok=True)
		bench = Path(bench).resolve()
		self.state = {
			"pr": int(pr),
			"requirement": requirement,
			"site": site,
			"bench": str(bench),
			"bench_cmd": bench_cmd,
			"repo": repo,
			"app": app,
		}
		if self.git("status", "--porcelain", "--untracked-files=no"):
			raise Failure(f"{self.app_dir} has uncommitted changes")
		self.state["original_branch"] = self.git("rev-parse", "--abbrev-ref", "HEAD")

		meta = json.loads(
			sh(
				"gh",
				"pr",
				"view",
				pr,
				"--repo",
				repo,
				"--json",
				"number,title,body,url,baseRefName,headRefOid,files",
			)
		)
		write(self.workdir / "pr.json", meta)
		url = f"https://github.com/{repo}"
		self.git("fetch", "--quiet", url, meta["baseRefName"])
		self.state["base_sha"] = self.git("rev-parse", "FETCH_HEAD")
		self.git("fetch", "--quiet", url, f"pull/{pr}/head")
		self.state["pr_head_sha"] = self.git("rev-parse", "FETCH_HEAD")
		if self.state["pr_head_sha"] != meta["headRefOid"]:
			raise Failure("fetched PR head does not match the PR's headRefOid; retry")
		apps = sh(*shlex.split(bench_cmd), "--site", site, "list-apps", cwd=bench).splitlines()
		self.state["apps"] = sorted(
			{line.split()[0] for line in apps if line.strip() and not line.startswith(" ")}
		)
		self._check_versions(meta["baseRefName"], apps)

		base_branch, head_branch = f"review-{pr}-base", f"review-{pr}-head"
		self.git("branch", "-f", base_branch, self.state["base_sha"])
		self.git("checkout", "--quiet", "-B", head_branch, self.state["base_sha"])
		merged = subprocess.run(
			["git", "-C", self.app_dir, "merge", "--no-ff", "--no-edit", self.state["pr_head_sha"]],
			capture_output=True,
			text=True,
			env={**os.environ, **GIT_ENV},
		)
		if merged.returncode:
			self.git("merge", "--abort", check=False)
			self.git("checkout", "--quiet", self.state["original_branch"])
			self.git("branch", "-D", base_branch, head_branch, check=False)
			raise Failure(f"PR does not merge cleanly onto {meta['baseRefName']}:\n{merged.stdout}")
		self.state["head_sha"] = self.git("rev-parse", "HEAD")
		self.git("checkout", "--quiet", self.state["original_branch"])
		self.state["branches"] = [base_branch, head_branch]
		(self.workdir / "pr.diff").write_text(
			self.git("diff", self.state["base_sha"], self.state["head_sha"])
		)

		self._requirement(requirement)
		snapshot = self.workdir / "scripts"
		shutil.rmtree(snapshot, ignore_errors=True)
		shutil.copytree(SCRIPTS, snapshot, ignore=shutil.ignore_patterns("__pycache__"))
		self.state["skill_source"] = str(SCRIPTS)
		(self.workdir / ".scripts").write_text(str(snapshot))
		(self.workdir / ".ui-password").write_text(secrets.token_urlsafe(24))
		for name in ("s0.py", "expect.json"):
			if not (self.workdir / name).exists():
				shutil.copy(SCRIPTS / "templates" / name, self.workdir / name)
		write(self.state_path, self.state)
		print(
			f"initialised {self.workdir}\n  base {self.state['base_sha']}\n  head {self.state['head_sha']} (base + PR)"
		)

	def _check_versions(self, base_ref, list_apps):
		"""The PR's base, the bench's Frappe and the site's ERPNext must share a major version.

		A version-15 PR needs a v15 bench and a v15 site: the run migrates the site to
		the base code, and a site cannot migrate down a major version.
		"""
		app = self.state["app"]
		base = _major(self.git("show", f"{self.state['base_sha']}:{app}/__init__.py"))
		framework = _major(Path(self.state["bench"], "apps", "frappe", "frappe", "__init__.py").read_text())
		installed = next(
			(
				_major(line.split()[1])
				for line in list_apps
				if line.split()[:1] == [app] and len(line.split()) > 1
			),
			None,
		)
		self.state["versions"] = {"base": base, "frappe": framework, "site": installed}
		if base is None:
			raise Failure(f"cannot read the {app} version at the base commit of {base_ref}")
		if framework != base:
			raise Failure(
				f"the PR targets {base_ref} ({app} v{base}), but this bench runs Frappe v{framework}. "
				f"Use a bench on Frappe v{base}."
			)
		if installed is not None and installed != base:
			raise Failure(
				f"site {self.state['site']} has {app} v{installed} installed, but the PR targets v{base}. "
				f"Use a site on {app} v{base}."
			)
		print(f"versions: base {base_ref} v{base}, bench Frappe v{framework}, site {app} v{installed or '?'}")

	def _requirement(self, ref):
		m = re.match(
			r"(?:https://github\.com/([\w.-]+/[\w.-]+)/issues/(\d+))|(?:([\w.-]+/[\w.-]+)#(\d+))", ref
		)
		if m:
			repo, number = (m[1], m[2]) if m[1] else (m[3], m[4])
			issue = json.loads(
				sh("gh", "issue", "view", number, "--repo", repo, "--json", "number,title,body,url,comments")
			)
			write(self.workdir / "requirement.json", {"source": "github", **issue})
			print("requirement: GitHub issue saved to requirement.json")
		else:
			write(self.workdir / "requirement.json", {"source": "ticket", "ref": ref, "text": None})
			print("requirement: support ticket; paste its full text into requirement.json 'text'")

	# ------------------------------------------------------------ analyze

	def analyze(self):
		from analyze import analyze, generate_plan

		apps_dir = Path(self.state["bench"], "apps")
		analysis = analyze(
			apps_dir, self.state["app"], self.state["apps"], self.state["base_sha"], self.state["head_sha"]
		)
		write(self.workdir / "analysis.json", analysis)
		plan = generate_plan(analysis, self.state["pr"])
		write(self.workdir / "plan.generated.json", plan)
		if not (self.workdir / "plan.json").exists():
			write(self.workdir / "plan.json", plan)
		if plan["ui"] and not (self.workdir / "ui.spec.mjs").exists():
			shutil.copy(SCRIPTS / "templates" / "ui.spec.mjs", self.workdir / "ui.spec.mjs")
			print(f"the PR changes {len(analysis['ui_files'])} UI files: write ui.spec.mjs")
		print(
			f"{len(analysis['symbols'])} changed symbols, {len(analysis['settings'])} settings, "
			f"{len(plan['variants'])} variants, {len(plan['flips'])} flips"
		)

	# ------------------------------------------------------------ lock

	def lock(self, reason):
		for name in ("plan.json", "expect.json"):
			if not (self.workdir / name).exists():
				raise Failure(f"{name} is missing")
		_validate_expect(read(self.workdir / "expect.json"))
		if read(self.workdir / "plan.json").get("ui") and not (self.workdir / "ui.spec.mjs").exists():
			raise Failure("the PR changes UI files: write ui.spec.mjs (Playwright scenarios) before locking")
		path = self.workdir / "lock.json"
		lock = read(path) if path.exists() else {"history": []}
		if lock["history"] and not reason:
			raise Failure("re-locking needs --reason: the report lists every lock and its reason")
		hashes = file_hashes(self.workdir)
		lock["history"].append({"hashes": hashes, "reason": reason or "initial", "at": _now()})
		lock["current"] = hashes
		write(path, lock)
		print("locked", hashes)

	# ------------------------------------------------------------ run

	def run(self, keep_data=False):
		lock = read(self.workdir / "lock.json") if (self.workdir / "lock.json").exists() else None
		if not lock or lock["current"] != file_hashes(self.workdir):
			raise Failure(
				"a locked file (plan.json, s0.py, expect.json, ui.spec.mjs, or the scripts snapshot) "
				"changed since the lock, or there is no lock: run `lock`"
			)
		plan, analysis = read(self.workdir / "plan.json"), read(self.workdir / "analysis.json")
		runs = self.workdir / "runs"
		run_id = 1 + max([int(p.name) for p in runs.glob("*") if p.name.isdigit()] or [0])
		rundir = runs / str(run_id)
		record = {
			"run_id": run_id,
			"prefix": f"PR{self.state['pr']}R{run_id}",
			"lock": lock["current"],
			"base_sha": self.state["base_sha"],
			"head_sha": self.state["head_sha"],
			"site": self.state["site"],
			"started": _now(),
			"status": "running",
			"sessions": [],
		}
		write(self.workdir / "run.json", record)
		scheduler_was_paused = bool(self._site_config().get("pause_scheduler"))
		record["scheduler_was_paused"] = scheduler_was_paused
		record["ui"] = bool(plan.get("ui"))
		record["keep_data"] = keep_data
		try:
			if record["ui"]:
				self._ui_setup()
			self._checkout(f"review-{self.state['pr']}-base")
			self._bench("migrate")
			self._bench("scheduler", "pause")
			self._session(record, "probe", side="base")
			self._session(record, "preflight")
			record["active"] = {"base": self._active_variants(plan, rundir, "base", record)}
			for vid in record["active"]["base"]:
				self._session(record, "switch", variant=vid)
				self._session(record, "base_build", variant=vid)
			# A flip needs both settings on both codes; the analysis only makes such flips.
			flips = [f for f in plan["flips"] if set(f) <= set(record["active"]["base"])]
			record["flips"] = flips
			for a, b in flips:
				self._session(record, "switch", variant=b)
				self._session(record, "base_flip", flip=[a, b])
			if record["ui"]:
				self._session(record, "switch", variant="v0")
				self._session(record, "ui_user")
				self._ui_phase(record, "base", "UB")
			self._checkout(f"review-{self.state['pr']}-head")
			if analysis["needs_migrate"]:
				self._bench("migrate")
			# settings that only the PR code has exist now: record their site values
			self._session(record, "probe", side="head")
			record["active"]["head"] = self._active_variants(plan, rundir, "head", record)
			for vid in record["active"]["head"]:
				self._session(record, "switch", variant=vid)
				self._session(record, "head_variant", variant=vid)
			if record["ui"]:
				self._session(record, "switch", variant="v0")
				self._ui_phase(record, "head", "UH")
			record["status"] = "complete"
		except Failure as e:
			record["status"] = "failed"
			record["error"] = str(e)[-3000:]
		finally:
			self._cleanup(record, scheduler_was_paused)
			record["finished"] = _now()
			write(rundir / "run.json", record)
			write(self.workdir / "run.json", record)
		print(
			f"run {run_id}: {record['status']}{' - ' + record.get('error', '')[:500] if record['status'] != 'complete' else ''}"
		)

	def _active_variants(self, plan, rundir, side, record):
		"""Variants that this code side supports, less those equal to the site defaults."""
		originals = read(rundir / "settings-original.json")
		company_defaults = read(rundir / "company-defaults.json")
		skipped = record.setdefault("skipped_variants", {})
		active = []
		for v in plan["variants"]:
			if side not in v.get("sides", ("base", "head")):
				continue
			same_singles = all(
				str(originals.get(dt, {}).get(f) or "") == str(val or "")
				for dt, values in v.get("singles", {}).items()
				for f, val in values.items()
			)
			same_company = all(
				str(company_defaults.get(f) or "0") == str(val or "0")
				for f, val in v.get("company", {}).items()
			)
			if v["id"] != "v0" and same_singles and same_company:
				skipped[v["id"]] = "same as default on this site"
			else:
				active.append(v["id"])
		return active

	def _cleanup(self, record, scheduler_was_paused):
		errors = []
		for step in (
			lambda: self._session(record, "restore"),
			lambda: self._checkout(self.state["original_branch"]),
			lambda: None if record.get("keep_data") else self._delete_data(record),
			lambda: None if scheduler_was_paused else self._bench("scheduler", "resume"),
			# assets were built from the review branches: rebuild them for the original code
			lambda: self._bench_global("build", "--app", self.state["app"]) if record.get("ui") else None,
		):
			try:
				step()
			except Failure as e:
				errors.append(str(e)[-500:])
		if errors:
			record["cleanup_errors"] = errors

	def _delete_data(self, record):
		started = self.workdir / "runs" / str(record["run_id"]) / "site-started.txt"
		since = started.read_text().strip() if started.exists() else None
		try:
			self._session(record, "cleanup", prefix=record["prefix"], since=since)
			record["data"] = "deleted"
		except Failure:
			record["data"] = "cleanup failed"
			raise

	def cleanup(self, run_id=None):
		"""Delete the site data of a run that kept it (or whose cleanup failed)."""
		run_id = run_id or read(self.workdir / "run.json")["run_id"]
		record = read(self.workdir / "runs" / str(run_id) / "run.json")
		write(self.workdir / "run.json", record)  # the engine reads the current run from here
		self._delete_data(record)
		write(self.workdir / "runs" / str(run_id) / "run.json", record)
		print(f"run {run_id}: review data deleted from {record['site']}")

	def _session(self, record, command, **args):
		n = len(record["sessions"]) + 1
		label = "-".join(
			[command, *[str(v) if not isinstance(v, list) else "-".join(v) for v in args.values()]]
		)
		code = (
			f"exec(open({str(SCRIPTS / 'engine.py')!r}).read(), globals()); "
			f"engine_main({str(self.workdir)!r}, {command!r}, {json.dumps(json.dumps(args))})"
		)
		out = subprocess.run(
			[*self._bench_cmd(), "--site", self.state["site"], "console"],
			input=f"{code}\nexit\ny\n",
			capture_output=True,
			text=True,
			cwd=self.state["bench"],
		)
		log = self.workdir / "runs" / str(record["run_id"]) / "logs" / f"{n:03d}-{label}.log"
		log.parent.mkdir(parents=True, exist_ok=True)
		log.write_text(out.stdout + out.stderr)
		ok = f"ENGINE_OK {command}" in out.stdout
		record["sessions"].append({"n": n, "session": label, "ok": ok})
		write(self.workdir / "run.json", record)
		if not ok:
			raise Failure(f"session {label} failed, see {log}:\n{out.stdout[-1500:]}")

	def _bench_cmd(self):
		return shlex.split(self.state.get("bench_cmd", "bench"))

	def _bench(self, *args):
		sh(*self._bench_cmd(), "--site", self.state["site"], *args, cwd=self.state["bench"])

	def _bench_global(self, *args):
		sh(*self._bench_cmd(), *args, cwd=self.state["bench"])

	# ------------------------------------------------------------ UI

	def _ui_setup(self):
		"""Pinned Playwright and Chromium in <workdir>/.ui, before the site is touched."""
		ui = self.workdir / ".ui"
		ui.mkdir(exist_ok=True)
		if not (ui / "package.json").exists():
			write(ui / "package.json", {"name": "review-ui", "private": True, "type": "module"})
		if not (ui / "node_modules" / "playwright").exists():
			sh("npm", "install", "--no-audit", "--no-fund", f"playwright@{PLAYWRIGHT}", cwd=ui)
		sh("npx", "playwright", "install", "chromium", cwd=ui)

	def _ui_phase(self, record, side, target):
		"""Build this side's assets, serve this side's code, run every UI scenario."""
		self._bench_global("build", "--app", self.state["app"])
		with socket.socket() as probe:
			probe.bind(("127.0.0.1", 0))
			port = probe.getsockname()[1]
		log = self.workdir / "runs" / str(record["run_id"]) / "logs" / f"serve-{side}.log"
		log.parent.mkdir(parents=True, exist_ok=True)
		with open(log, "w") as out:
			server = subprocess.Popen(
				[
					*self._bench_cmd(),
					"--site",
					self.state["site"],
					"serve",
					"--port",
					str(port),
					"--noreload",
				],
				cwd=self.state["bench"],
				stdout=out,
				stderr=subprocess.STDOUT,
			)
		url = f"http://127.0.0.1:{port}"
		try:
			_wait_for(f"{url}/api/method/ping", seconds=180)
			result = subprocess.run(
				[
					"node",
					str(SCRIPTS / "ui" / "runner.mjs"),
					str(self.workdir),
					str(record["run_id"]),
					side,
					target,
					url,
				],
				capture_output=True,
				text=True,
			)
			(log.parent / f"ui-{side}.log").write_text(result.stdout + result.stderr)
			ok = f"UI_OK {side}" in result.stdout
			record["sessions"].append({"n": len(record["sessions"]) + 1, "session": f"ui-{side}", "ok": ok})
			if not ok:
				raise Failure(
					f"UI run on {side} code failed:\n{result.stdout[-1000:]}\n{result.stderr[-1500:]}"
				)
		finally:
			server.terminate()
			server.wait(timeout=30)

	def _checkout(self, branch):
		if self.git("status", "--porcelain", "--untracked-files=no"):
			raise Failure(f"{self.app_dir} has uncommitted changes; not switching to {branch}")
		self.git("checkout", "--quiet", branch)

	def _site_config(self):
		path = Path(self.state["bench"], "sites", self.state["site"], "site_config.json")
		return read(path) if path.exists() else {}

	def restore(self):
		record = read(self.workdir / "run.json")
		paused = record.get("scheduler_was_paused", False)
		self._cleanup(record, paused)
		print("restored settings, scheduler and branch", record.get("cleanup_errors", ""))

	# ------------------------------------------------------------ report

	def report(self):
		from verdict import evaluate

		record = read(self.workdir / "run.json")
		result = evaluate(self.workdir, record["run_id"])
		write(self.workdir / "verdict.json", result)
		(self.workdir / "report.md").write_text(self._render(record, result))
		print(f"verdict: {result['verdict']}  ->  {self.workdir / 'report.md'}")

	def _render(self, record, result):
		from render import render

		return render(self.workdir, self.state, record, result)


def _major(text):
	"""Major version from a version string or from an __init__.py that defines __version__."""
	m = re.search(r"""__version__\s*=\s*["'](\d+)""", text) or re.match(r"v?(\d+)\.", text.strip())
	return int(m[1]) if m else None


def _wait_for(url, seconds):
	deadline = time.time() + seconds
	while time.time() < deadline:
		try:
			with urllib.request.urlopen(url, timeout=5) as r:
				if r.status == 200:
					return
		except OSError:
			time.sleep(2)
	raise Failure(f"{url} did not answer within {seconds}s")


def _validate_expect(expect):
	for a in expect.get("assertions", []):
		missing = {"path", "snapshot", "equals", "why"} - set(a)
		if missing:
			raise Failure(f"assertion {a} lacks {sorted(missing)}")
		if a["snapshot"] not in ("base", "head", "base_legacy", "head_legacy", "ui_base", "ui_head"):
			raise Failure(
				f"assertion snapshot must be base, head, base_legacy, head_legacy, ui_base or ui_head: {a}"
			)
	for rule in expect.get("allowed_changes", []):
		missing = {"comparison", "path", "reason"} - set(rule)
		if missing:
			raise Failure(f"allowed change {rule} lacks {sorted(missing)}")


def _now():
	return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def main():
	parser = argparse.ArgumentParser(
		description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
	)
	parser.add_argument("command", choices=["init", "analyze", "lock", "run", "report", "restore", "cleanup"])
	parser.add_argument("--workdir", required=True)
	parser.add_argument("--pr")
	parser.add_argument("--requirement")
	parser.add_argument("--site")
	parser.add_argument("--bench")
	parser.add_argument("--repo", default="frappe/erpnext")
	parser.add_argument("--app", default="erpnext")
	parser.add_argument("--bench-cmd", default="bench", help="how to call bench, e.g. '~/.venv/bin/bench'")
	parser.add_argument("--reason")
	parser.add_argument("--keep-data", action="store_true", help="leave the review companies on the site")
	parser.add_argument("--run", type=int, help="cleanup: the run whose data to delete (default: latest)")
	args = parser.parse_args()
	snapshot = Path(args.workdir).resolve() / "scripts" / "review.py"
	if args.command != "init" and snapshot.exists() and Path(__file__).resolve() != snapshot:
		os.execv(sys.executable, [sys.executable, str(snapshot), *sys.argv[1:]])
	review = Review(args.workdir)
	if args.command != "init" and not review.state:
		sys.exit(f"error: {args.workdir} has no review: run `init` first")
	try:
		if args.command == "init":
			if not all([args.pr, args.requirement, args.site, args.bench]):
				parser.error("init needs --pr, --requirement, --site and --bench")
			review.init(args.pr, args.requirement, args.site, args.bench, args.repo, args.app, args.bench_cmd)
		elif args.command == "lock":
			review.lock(args.reason)
		elif args.command == "run":
			review.run(keep_data=args.keep_data)
		elif args.command == "cleanup":
			review.cleanup(args.run)
		else:
			getattr(review, args.command)()
	except Failure as e:
		sys.exit(f"error: {e}")


if __name__ == "__main__":
	main()
