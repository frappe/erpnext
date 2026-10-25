import frappe
from frappe.permissions import get_doctypes_with_custom_docperms
from frappe.utils import cint

from erpnext.setup.install import get_role_rules

DOCTYPES = ("Payment Terms Template",)
SAVEPOINT = "remove_all_role_from_payment_terms_template"


def execute():
	customised = get_doctypes_with_custom_docperms()
	for doctype in DOCTYPES:
		if doctype not in customised:
			continue
		removed = False
		for rule in get_role_rules(doctype, "All"):
			if not cint(rule.permlevel) and remove_rule(doctype, rule.name):
				removed = True
		if removed:
			frappe.clear_cache(doctype=doctype)


def remove_rule(doctype: str, rule_name: str) -> bool:
	try:
		frappe.db.savepoint(SAVEPOINT)
		frappe.delete_doc("Custom DocPerm", rule_name, ignore_permissions=True)
		print(f"{doctype} / All: removed")
		return True
	except Exception:
		frappe.db.rollback(save_point=SAVEPOINT)
		frappe.log_error(
			title="Could not remove permission", message=f"{doctype} / All\n\n{frappe.get_traceback()}"
		)
		return False
