import frappe
from frappe.permissions import get_all_perms, get_doctypes_with_custom_docperms
from frappe.utils import cint

GRANTS = {
	"Payment Terms Template": {
		"Maintenance Manager": ("read",),
		"Maintenance User": ("read",),
		"Purchase Manager": ("read",),
		"Purchase User": ("read",),
		"Sales Manager": ("read",),
		"Sales User": ("read",),
		"Purchase Master Manager": ("select",),
		"Sales Master Manager": ("select",),
	},
	"POS Invoice": {
		"Sales Manager": ("read",),
		"Sales User": ("read",),
	},
	"Serial and Batch Bundle": {
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
	customised = get_doctypes_with_custom_docperms()
	for doctype, roles in GRANTS.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		if doctype not in customised:
			continue
		added = False
		for role, ptypes in roles.items():
			if mirror_role(doctype, role, ptypes):
				added = True
		if added:
			frappe.clear_cache(doctype=doctype)


def mirror_role(doctype, role, ptypes):
	if not frappe.db.exists("Role", role):
		return False
	rules = []
	for rule in get_all_perms(role):
		if rule.parent == doctype and not cint(rule.permlevel):
			rules.append(rule)
	if not rules:
		return insert_rule(doctype, role, ptypes)
	if is_unedited_release_copy(doctype, role, rules):
		return widen_rule(doctype, role, ptypes, rules[0])
	rights = ", ".join(ptypes)
	if has_full_rule(rules, ptypes):
		print(f"{doctype} / {role}: kept, the site's rule already grants {rights}")
	else:
		print(f"{doctype} / {role}: kept, the site's rule does not grant {rights}")
	return False


def is_unedited_release_copy(doctype, role, rules):
	previous = PREVIOUS_SHIPPED_RULES.get((doctype, role))
	if previous is None:
		return False
	if len(rules) != 1:
		return False
	if cint(rules[0].if_owner):
		return False
	granted = set()
	for field in frappe.get_meta("Custom DocPerm").fields:
		if field.fieldtype != "Check" or field.fieldname == "if_owner":
			continue
		if frappe.db.has_column("Custom DocPerm", field.fieldname) and cint(rules[0].get(field.fieldname)):
			granted.add(field.fieldname)
	return granted == set(previous)


def has_full_rule(rules, ptypes):
	for rule in rules:
		if cint(rule.if_owner):
			continue
		missing = False
		for ptype in ptypes:
			if not cint(rule.get(ptype)):
				missing = True
				break
		if not missing:
			return True
	return False


def widen_rule(doctype, role, ptypes, rule):
	try:
		frappe.db.savepoint(SAVEPOINT)
		row = frappe.get_doc("Custom DocPerm", rule.name)
		for ptype in ptypes:
			row.set(ptype, 1)
		row.save(ignore_permissions=True)
		print(f"{doctype} / {role}: widened, unedited copy of the release rule")
		return True
	except Exception:
		log_failure("Could not widen permission", doctype, role)
		return False


def insert_rule(doctype, role, ptypes):
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
		print(f"{doctype} / {role}: added {', '.join(ptypes)}")
		return True
	except Exception:
		log_failure("Could not add permission", doctype, role)
		return False


def log_failure(title, doctype, role):
	frappe.db.rollback(save_point=SAVEPOINT)
	frappe.log_error(title=title, message=f"{doctype} / {role}\n\n{frappe.get_traceback()}")
