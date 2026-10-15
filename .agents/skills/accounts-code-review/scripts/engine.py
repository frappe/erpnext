"""In-site session runner for accounts-code-review. review.py drives it; do not run phases by hand.

One console session runs one command:

    exec(open("<skill dir>/scripts/engine.py").read(), globals())
    engine_main("<workdir>", "<command>", "<json args>")

Company kinds, per variant v (and per flip a-b for FC / FT):
    C   control:   built on base code, legacy acted on base code
    T   treatment: built on base code, rescanned and legacy acted on PR code
    H   head:      built on PR code
    FC  flip control:   built under a, acted on under b, all base code
    FT  flip treatment: built under a on base code, acted on under b on PR code
    UB  UI, base code, default variant: the browser may change it freely
    UH  UI, PR code, default variant
"""

import importlib.util
import json
import sys
import traceback
from pathlib import Path


def engine_main(workdir, command, args_json="{}"):
	import frappe

	scripts = Path(workdir, ".scripts").read_text().strip()  # written by review.py init
	if scripts not in sys.path:
		sys.path.insert(0, scripts)
	for name in ("pr_ledger", "library"):
		sys.modules.pop(name, None)

	session = _Session(Path(workdir), json.loads(args_json))
	try:
		_run_jobs_now()
		getattr(session, f"cmd_{command}")()
		session.save_created()
		frappe.db.commit()
		print(f"ENGINE_OK {command}")
	except Exception:
		traceback.print_exc()
		frappe.db.rollback()
		print(f"ENGINE_FAIL {command}")


def _run_jobs_now():
	"""Run every enqueued job inline, in order, so no worker races the snapshot."""
	import frappe
	import frappe.utils.background_jobs as bj

	original = bj.enqueue

	def enqueue_now(method, *args, **kwargs):
		kwargs["now"] = True
		kwargs.pop("enqueue_after_commit", None)
		return original(method, *args, **kwargs)

	for module in list(sys.modules.values()):
		if getattr(module, "enqueue", None) is original:
			module.enqueue = enqueue_now
	frappe.enqueue = bj.enqueue = enqueue_now


class _Session:
	def __init__(self, workdir, args):
		import frappe
		import library
		import pr_ledger

		self.frappe, self.L, self.library = frappe, pr_ledger, library
		self.workdir = workdir
		self.args = args
		self.plan = json.loads((workdir / "plan.json").read_text())
		self.run = json.loads((workdir / "run.json").read_text())
		self.variants = {v["id"]: v for v in self.plan["variants"]}
		self.rundir = workdir / "runs" / str(self.run["run_id"])
		self.snapdir = self.rundir / "snapshots"
		self.snapdir.mkdir(parents=True, exist_ok=True)
		self.s0 = _load_s0(workdir)

	# ------------------------------------------------------------ commands

	def cmd_probe(self):
		"""Record the site's clock and original singles; resolve company field defaults."""
		(self.rundir / "site-started.txt").write_text(self.frappe.utils.now())
		self.L.record_originals(self.plan["variants"], self.workdir / "settings-original.json")
		meta = self.frappe.get_meta("Company")
		defaults = {}
		for v in self.plan["variants"]:
			for field in v.get("company", {}):
				df = meta.get_field(field)
				defaults[field] = df.default if df else None
		_write(self.workdir / "runs" / str(self.run["run_id"]) / "company-defaults.json", defaults)

	def cmd_preflight(self):
		"""Build every scenario once in a throwaway company, then roll it all back."""
		results = {}
		try:
			lab = self._lab("P", "preflight", "v0")
			for s in self._scenarios():
				lab.current = s["id"]
				lab.attempt(f"build-{s['id']}", lambda s=s: s["build"](lab))
			results = dict(lab.outcomes)
		finally:
			self.frappe.db.rollback()
		_write(self.rundir / "preflight.json", results)
		_write(
			self.rundir / "scenarios.json",
			[
				{"id": s["id"], "title": s["title"], "flows": s["flows"], "source": s["source"]}
				for s in self._scenarios()
			],
		)
		print("PREFLIGHT", results)

	def cmd_ui_user(self):
		"""A fixed review user for the browser. Its password lives only in the workdir."""
		email, password = "review-ui@example.com", (self.workdir / ".ui-password").read_text().strip()
		if not self.frappe.db.exists("User", email):
			self.frappe.get_doc(
				{"doctype": "User", "email": email, "first_name": "Review", "send_welcome_email": 0}
			).insert(ignore_permissions=True)
			self.L.CREATED.setdefault("User", []).append(email)
		user = self.frappe.get_doc("User", email)
		user.add_roles(
			"System Manager",
			"Accounts Manager",
			"Accounts User",
			"Stock Manager",
			"Sales Manager",
			"Purchase Manager",
		)
		user.new_password = password
		user.save(ignore_permissions=True)

	def cmd_cleanup(self):
		"""Delete every record of run args["prefix"]; fail if anything is left."""
		created = self._created()
		left = self.L.delete_review_data(self.args["prefix"], created, self.args["since"])
		if left:
			raise RuntimeError(f"review data left on the site after cleanup: {left}")
		print("CLEANED", self.args["prefix"])

	def save_created(self):
		"""Merge this session's CREATED records into <workdir>/site-created.json."""
		if not self.L.CREATED:
			return
		known = self._created()
		for doctype, names in self.L.CREATED.items():
			known[doctype] = sorted(set(known.get(doctype, [])) | set(names))
		_write(self.workdir / "site-created.json", known)
		self.L.CREATED.clear()

	def _created(self):
		path = self.workdir / "site-created.json"
		return json.loads(path.read_text()) if path.exists() else {}

	def cmd_switch(self):
		originals = json.loads((self.workdir / "settings-original.json").read_text())
		target = self.L.target_singles(self.variants[self.args["variant"]], originals)
		self.L.save_singles(target)
		print("SWITCHED", self.args["variant"], target)

	def cmd_restore(self):
		path = self.workdir / "settings-original.json"
		if path.exists():
			self.L.save_singles(json.loads(path.read_text()))
			print("RESTORED", path.read_text())

	def cmd_base_build(self):
		vid = self.args["variant"]
		self._assert_variant(vid)
		for kind in ("C", "T"):
			self._build(kind, vid, vid)
		for a, b in self.plan["flips"]:
			if a == vid:
				for kind in ("FC", "FT"):
					self._build(kind, f"{a}-{b}", a)
		self._legacy("C", vid, vid)
		if vid == "v0" and self.plan.get("ui"):
			self._build("UB", vid, vid)

	def cmd_base_flip(self):
		a, b = self.args["flip"]
		self._assert_variant(b)
		self._legacy("FC", f"{a}-{b}", b)

	def cmd_head_variant(self):
		vid = self.args["variant"]
		self._assert_variant(vid)
		lab = self._lab("T", vid, vid)
		self._snapshot(lab, f"T-{vid}-rescan")
		self._legacy("T", vid, vid)
		self._build("H", vid, vid)
		for a, b in self.plan["flips"]:
			if b == vid:
				self._legacy("FT", f"{a}-{b}", b)
		if vid == "v0" and self.plan.get("ui"):
			self._build("UH", vid, vid)

	# ------------------------------------------------------------ steps

	def _assert_variant(self, vid):
		originals = json.loads((self.workdir / "settings-original.json").read_text())
		wrong = self.L.singles_mismatch(self.L.target_singles(self.variants[vid], originals))
		if wrong:
			raise AssertionError(f"site singles are not variant {vid}: {wrong}")

	def _company(self, kind, key):
		prefix = self.run["prefix"]
		return f"{prefix} {kind} {key}", f"{prefix}{kind}{key}".replace("-", "")

	def _lab(self, kind, key, settings_vid):
		name, abbr = self._company(kind, key)
		ctx = self.L.setup_company(
			name, abbr, self.variants[settings_vid].get("company"), self.plan.get("company_profile")
		)
		ctx = self.L.make_masters(ctx, self.run["prefix"], self.L.item_fields(self.plan.get("item_fields")))
		lab = self.L.Lab(ctx)
		saved = self._registry_path(kind, key)
		if saved.exists():
			state = json.loads(saved.read_text())
			lab.registry, lab.outcomes, lab.owners = (
				state["registry"],
				state["outcomes"],
				state.get("owners", {}),
			)
		return lab

	def _build(self, kind, key, settings_vid):
		lab = self._lab(kind, key, settings_vid)
		for s in self._scenarios():
			lab.current = s["id"]
			lab.attempt(f"build-{s['id']}", lambda s=s: s["build"](lab))
		self._save_registry(lab, kind, key)
		self._snapshot(lab, f"{kind}-{key}-built")
		if kind in ("UB", "UH"):
			names = self.L.name_map(lab)
			_write(
				self.rundir / "ui-targets" / f"{kind}.json",
				{"company": lab.ctx.company, "abbr": lab.ctx.abbr, "registry": lab.registry, "names": names},
			)

	def _legacy(self, kind, key, settings_vid):
		lab = self._lab(kind, key, settings_vid)
		built = self._built_outcomes(kind, key)
		for s in self._scenarios():
			if f"build-{s['id']}" in built:
				lab.current = s["id"]
				lab.attempt(f"legacy-{s['id']}", lambda s=s: s["legacy"](lab))
		self._save_registry(lab, kind, key)
		self._snapshot(lab, f"{kind}-{key}-legacy")

	def _built_outcomes(self, kind, key):
		snap = json.loads((self.snapdir / f"{kind}-{key}-built.json").read_text())
		return {k for k, v in snap["outcomes"].items() if v == "ok"}

	def _scenarios(self):
		scenarios = [{**s, "source": "library"} for s in self.library.SCENARIOS]
		scenarios += [{**s, "source": "s0"} for s in getattr(self.s0, "SCENARIOS", [])]
		ids = [s["id"] for s in scenarios]
		assert len(ids) == len(set(ids)), f"duplicate scenario ids: {ids}"
		return scenarios

	def _reports(self, ctx):
		reports = self.L.standard_reports(ctx)
		if self.s0 and hasattr(self.s0, "reports"):
			reports.update(self.s0.reports(ctx))
		return reports

	def _snapshot(self, lab, name):
		_write(self.snapdir / f"{name}.json", self.L.snapshot(lab, self._reports(lab.ctx)))
		print("SNAPSHOT", name)

	def _registry_path(self, kind, key):
		return self.workdir / "runs" / str(self.run["run_id"]) / "registry" / f"{kind}-{key}.json"

	def _save_registry(self, lab, kind, key):
		"""Registry and outcomes carry across sessions, so every later snapshot includes them."""
		_write(
			self._registry_path(kind, key),
			{"registry": lab.registry, "outcomes": lab.outcomes, "owners": lab.owners},
		)
		labels = self.rundir / "labels.json"
		known = json.loads(labels.read_text()) if labels.exists() else {}
		_write(labels, {**known, **lab.owners})


def _load_s0(workdir):
	path = workdir / "s0.py"
	if not path.exists():
		return None
	spec = importlib.util.spec_from_file_location("review_s0", path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def _write(path, data):
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(data, indent=1, sort_keys=True, default=str))
