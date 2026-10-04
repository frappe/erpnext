import json

import frappe
from frappe.utils import cint

from erpnext.setup.install import get_role_rules

GRANTS = {
	"Payment Terms Template": {
		"Maintenance Manager": ("read",),
		"Maintenance User": ("read",),
		"Manufacturing Manager": ("read",),
		"Purchase Manager": ("read",),
		"Purchase User": ("read",),
		"Sales Manager": ("read",),
		"Sales User": ("read",),
		"HR Manager": ("select",),
		"Purchase Master Manager": ("select",),
		"Sales Master Manager": ("select",),
	},
	"Payment Term": {
		"Manufacturing Manager": ("select",),
	},
	"Serial and Batch Bundle": {
		"Sales User": ("select",),
	},
	"POS Invoice": {
		"Sales Manager": ("read",),
		"Sales User": ("read",),
	},
	"Asset": {
		"Accounts Manager": ("select",),
		"System Manager": ("select",),
	},
}

PREVIOUS_SHIPPED_RULES = {
	("POS Invoice", "Sales Manager"): ("select",),
	("POS Invoice", "Sales User"): ("select",),
}

PTYPES = (
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"amend",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
)

SAVEPOINT = "mirror_release_perms_to_custom_docperm"


def execute():
	mirror_rules(GRANTS)


def mirror_rules(grants: dict):
	if not frappe.db.exists("DocType", "Permission Log"):
		print(
			"Permission Log is not installed on this site, so a rule that was created and later deleted "
			"cannot be told apart from one that never existed. Skipping rather than re-granting a rule "
			"the site may have removed."
		)
		return

	enabled = {"is_app_disabled": 0} if frappe.db.has_column("Custom DocPerm", "is_app_disabled") else {}
	for doctype, roles in grants.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype, **enabled}):
			continue
		logs = frappe.get_all(
			"Permission Log",
			filters={"for_doctype": "DocType", "for_document": doctype, "reference_type": "Custom DocPerm"},
			fields=["name", "status", "reference", "changes"],
		)
		rule_roles = {}
		changed_rules = set()
		for log in logs:
			rule = log.reference or log.name
			if log.status in ("Removed", "Updated"):
				changed_rules.add(rule)
			try:
				logged = json.loads(log.changes) or {}
			except (TypeError, ValueError):
				continue
			before = logged.get("from") or {}
			for values in (before, logged.get("to") or {}):
				if values.get("role"):
					level = values.get("permlevel", before.get("permlevel"))
					rule_roles.setdefault(rule, set()).add((values["role"], level))
		changed = set()
		for rule in changed_rules:
			pairs = rule_roles.get(rule, set())
			current = frappe.db.get_value("Custom DocPerm", rule, ["role", "permlevel"], as_dict=True)
			if current:
				pairs = pairs | {(current.role, current.permlevel)}
			for role, level in pairs:
				if not cint(level):
					changed.add(role)
		added = False
		for role, ptypes in roles.items():
			if mirror_role(doctype, role, ptypes, changed):
				added = True
		if added:
			frappe.clear_cache(doctype=doctype)


def mirror_role(doctype: str, role: str, ptypes: tuple, changed: set) -> bool:
	if not frappe.db.exists("Role", role):
		return False
	grant_flags = []
	for field in frappe.get_meta("Custom DocPerm").fields:
		if field.fieldtype != "Check" or field.fieldname in ("if_owner", "is_app_disabled"):
			continue
		if frappe.db.has_column("Custom DocPerm", field.fieldname):
			grant_flags.append(field.fieldname)
	rules = []
	has_disabled_rule = False
	for rule in get_role_rules(doctype, role):
		if cint(rule.permlevel):
			continue
		if cint(rule.get("is_app_disabled")):
			has_disabled_rule = True
		else:
			rules.append(rule)
	if rules:
		for rule in rules:
			if cint(rule.if_owner):
				continue
			grants_all = True
			for ptype in ptypes:
				if not cint(rule.get(ptype)):
					grants_all = False
					break
			if grants_all:
				return False
		previous = PREVIOUS_SHIPPED_RULES.get((doctype, role))
		if role not in changed and previous is not None and len(rules) == 1 and not cint(rules[0].if_owner):
			is_copy = True
			for flag in grant_flags:
				if cint(rules[0].get(flag)) != (flag in previous):
					is_copy = False
					break
			if is_copy:
				return widen_rule(doctype, role, ptypes, rules[0].name)
		print(f"{doctype} / {role}: kept, the site's rule does not grant {', '.join(ptypes)}")
		return False
	if role in changed:
		print(f"{doctype} / {role}: skipped, this site changed the rule")
		return False
	if has_disabled_rule:
		print(f"{doctype} / {role}: kept, the role's rule is disabled with its app")
		return False
	return insert_rule(doctype, role, ptypes)


def widen_rule(doctype: str, role: str, ptypes: tuple, rule_name: str) -> bool:
	try:
		frappe.db.savepoint(SAVEPOINT)
		values = {}
		for ptype in ptypes:
			values[ptype] = 1
		frappe.db.set_value("Custom DocPerm", rule_name, values)
		print(f"{doctype} / {role}: widened, unedited copy of the release rule")
		return True
	except Exception:
		log_failure("Could not widen permission", doctype, role)
		return False


def insert_rule(doctype: str, role: str, ptypes: tuple) -> bool:
	try:
		frappe.db.savepoint(SAVEPOINT)
		values = {
			"parent": doctype,
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": role,
			"permlevel": 0,
			"if_owner": 0,
			"select": 1 if "select" in ptypes else 0,
		}
		for ptype in PTYPES:
			values[ptype] = 1 if ptype in ptypes else 0
		row = frappe.new_doc("Custom DocPerm")
		row.update(values)
		row.insert(ignore_permissions=True)
		return True
	except Exception:
		log_failure("Could not add read permission", doctype, role)
		return False


def log_failure(title: str, doctype: str, role: str):
	frappe.db.rollback(save_point=SAVEPOINT)
	frappe.log_error(title=title, message=f"{doctype} / {role}\n\n{frappe.get_traceback()}")
