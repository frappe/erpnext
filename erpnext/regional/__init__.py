# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt


import frappe
from frappe import _

from erpnext import get_region


def check_deletion_permission(doc, method):
	region = get_region(doc.company)
	if region in ["Nepal"] and doc.docstatus != 0:
		frappe.throw(_("Deletion is not permitted for country {0}").format(region))


def rename_vat_settings(doc, method, old_name: str, new_name: str, merge: bool = False) -> None:
	"""Keep the VAT settings named after their company, as the VAT reports look them up by name."""
	for doctype in ("UAE VAT Settings", "South Africa VAT Settings"):
		if frappe.db.exists(doctype, old_name) and not frappe.db.exists(doctype, new_name):
			frappe.rename_doc(doctype, old_name, new_name, force=True, show_alert=False)
