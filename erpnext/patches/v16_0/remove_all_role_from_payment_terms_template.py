import frappe
from frappe.permissions import get_all_perms, get_doctypes_with_custom_docperms
from frappe.utils import cint

DOCTYPES = ("Payment Terms Template",)
SAVEPOINT = "remove_all_role_from_payment_terms_template"


def execute():
	customised = get_doctypes_with_custom_docperms()
	for doctype in DOCTYPES:
		if doctype not in customised:
			continue

		for perm in get_all_perms("All"):
			if perm.parent != doctype or cint(perm.permlevel):
				continue
			try:
				frappe.db.savepoint(SAVEPOINT)
				frappe.delete_doc("Custom DocPerm", perm.name, ignore_permissions=True)
				print(f"{doctype} / All: removed")
			except Exception:
				frappe.db.rollback(save_point=SAVEPOINT)
				frappe.log_error(
					title="Could not remove permission",
					message=f"{doctype} / All\n\n{frappe.get_traceback()}",
				)
		frappe.clear_cache(doctype=doctype)
