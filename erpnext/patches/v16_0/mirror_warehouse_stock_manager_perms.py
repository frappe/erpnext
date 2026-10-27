import frappe
from frappe.permissions import get_doctypes_with_custom_docperms

from erpnext.patches.v16_0.mirror_release_perms_to_custom_docperm import mirror_role
from erpnext.setup.install import get_changed_roles


def execute():
	if not frappe.db.exists("DocType", "Permission Log"):
		return
	if "Warehouse" not in get_doctypes_with_custom_docperms():
		return

	ptypes = ("read", "report", "print", "email")
	if mirror_role("Warehouse", "Stock Manager", ptypes, get_changed_roles("Warehouse")):
		frappe.clear_cache(doctype="Warehouse")
