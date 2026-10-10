import frappe
from frappe.permissions import get_doctypes_with_custom_docperms

from erpnext.patches.v16_0.mirror_release_perms_to_custom_docperm import mirror_role


def execute():
	if "Warehouse" not in get_doctypes_with_custom_docperms():
		return
	if mirror_role("Warehouse", "Stock Manager", ("read", "report", "print", "email")):
		frappe.clear_cache(doctype="Warehouse")
