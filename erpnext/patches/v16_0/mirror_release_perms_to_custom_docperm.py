import frappe
from frappe.permissions import get_all_perms, get_doctypes_with_custom_docperms
from frappe.utils import cint

from erpnext.setup.install import get_changed_roles

GRANTS = {
	"Payment Terms Template": {
		"Maintenance Manager": ("read",),
		"Maintenance User": ("read",),
		"Purchase Manager": ("read",),
		"Purchase User": ("read",),
		"Sales Manager": ("read",),
		"Sales User": ("read",),
		"HR Manager": ("select",),
		"Purchase Master Manager": ("select",),
		"Sales Master Manager": ("select",),
	},
	"POS Invoice": {
		"Sales Manager": ("read",),
		"Sales User": ("read",),
	},
	"Serial and Batch Bundle": {
		"Sales Manager": ("select",),
		"Sales User": ("select",),
	},
	"Sales Taxes and Charges Template": {
		"Accounts User": ("select",),
		"Sales Manager": ("select",),
		"Stock User": ("select",),
		"Purchase Manager": ("select",),
		"Purchase User": ("select",),
		"Manufacturing Manager": ("select",),
		"Manufacturing User": ("select",),
	},
	"Purchase Taxes and Charges Template": {
		"Stock User": ("select",),
	},
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

PREVIOUS_SHIPPED_RULES = {
	("POS Invoice", "Sales Manager"): ("select",),
	("POS Invoice", "Sales User"): ("select",),
}

SAVEPOINT = "mirror_release_perms_to_custom_docperm"


def execute():
	if not frappe.db.exists("DocType", "Permission Log"):
		print(
			"mirror_release_perms_to_custom_docperm: Permission Log is not installed on this site, "
			"so a rule that was created and later deleted cannot be told apart from one that never "
			"existed. Skipping rather than re-granting a rule the site may have removed."
		)
		return

	customised = get_doctypes_with_custom_docperms()
	for doctype, roles in GRANTS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		if doctype not in customised:
			continue

		changed = get_changed_roles(doctype)
		added = False
		for role, ptypes in roles.items():
			if mirror_role(doctype, role, ptypes, changed):
				added = True
		if added:
			frappe.clear_cache(doctype=doctype)


def mirror_role(doctype: str, role: str, ptypes: tuple, changed: set) -> bool:
	if not frappe.db.exists("Role", role):
		return False

	rules = []
	for perm in get_all_perms(role):
		if perm.parent == doctype and not cint(perm.permlevel):
			rules.append(perm)
	if rules:
		for rule in rules:
			if is_unedited_release_copy(doctype, role, rule, changed):
				return widen_rule(doctype, role, ptypes, rule)
		if not has_full_rule(rules, ptypes):
			print(f"{doctype} / {role}: kept, the site's rule does not grant {', '.join(ptypes)}")
		return False

	if role in changed:
		print(f"{doctype} / {role}: skipped, this site changed the rule")
		return False
	return insert_rule(doctype, role, ptypes)


def is_unedited_release_copy(doctype: str, role: str, rule, changed: set) -> bool:
	previous = PREVIOUS_SHIPPED_RULES.get((doctype, role))
	if previous is None:
		return False
	if role in changed:
		return False
	if cint(rule.if_owner):
		return False
	for field in frappe.get_meta("Custom DocPerm").fields:
		if field.fieldtype != "Check" or field.fieldname in ("if_owner", "is_app_disabled"):
			continue
		if not frappe.db.has_column("Custom DocPerm", field.fieldname):
			continue
		expected = 1 if field.fieldname in previous else 0
		if cint(rule.get(field.fieldname)) != expected:
			return False
	return True


def widen_rule(doctype: str, role: str, ptypes: tuple, rule) -> bool:
	missing = get_missing_ptypes(ptypes, rule)
	if not missing:
		return False
	try:
		frappe.db.savepoint(SAVEPOINT)
		row = frappe.get_doc("Custom DocPerm", rule.name)
		for ptype in missing:
			row.set(ptype, 1)
		row.save(ignore_permissions=True)
		print(f"{doctype} / {role}: widened, unedited copy of the release rule (added {', '.join(missing)})")
		return True
	except Exception:
		log_failure("Could not widen permission", doctype, role)
		return False


def has_full_rule(rules: list, ptypes: tuple) -> bool:
	for rule in rules:
		if cint(rule.if_owner):
			continue
		if not get_missing_ptypes(ptypes, rule):
			return True
	return False


def get_missing_ptypes(ptypes: tuple, existing) -> list:
	missing = []
	for ptype in ptypes:
		if not cint(existing.get(ptype)):
			missing.append(ptype)
	return missing


def insert_rule(doctype: str, role: str, ptypes: tuple) -> bool:
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

	try:
		frappe.db.savepoint(SAVEPOINT)
		row = frappe.new_doc("Custom DocPerm")
		row.update(values)
		row.insert(ignore_permissions=True)
		print(f"{doctype} / {role}: added {', '.join(ptypes)}")
		return True
	except Exception:
		log_failure("Could not add permission", doctype, role)
		return False


def log_failure(title: str, doctype: str, role: str):
	frappe.db.rollback(save_point=SAVEPOINT)
	frappe.log_error(title=title, message=f"{doctype} / {role}\n\n{frappe.get_traceback()}")
