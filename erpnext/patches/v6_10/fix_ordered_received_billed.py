from __future__ import unicode_literals
import frappe

def execute():
	not_null_patch_date = frappe.db.sql("""select date(creation) from `tabPatch Log` where patch='frappe.patches.v6_9.int_float_not_null'""")
	if not not_null_patch_date:
		return

	not_null_patch_date = not_null_patch_date[0][0]

	for doctype in ("Purchase Invoice", "Sales Invoice", "Purchase Order", "Delivery Note", "Installation Note", "Delivery Note", "Purchase Receipt"):
		for name in frappe.db.sql_list("""select name from `tab{doctype}`
			where docstatus > 0 and (date(creation) >= %(patch_date)s or date(modified) >= %(patch_date)s)""".format(doctype=doctype),
			{"patch_date": not_null_patch_date}):

			doc = frappe.get_doc(doctype, name)
			doc.update_qty(update_modified=False)
