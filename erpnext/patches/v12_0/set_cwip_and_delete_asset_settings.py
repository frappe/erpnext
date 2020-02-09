from __future__ import unicode_literals
import frappe
from frappe.utils import cint


def execute():
	'''Get 'Disable CWIP Accounting value' from Asset Settings, set it in 'Enable Capital Work in Progress Accounting' field
	in Company, delete Asset Settings '''

	if frappe.db.exists("DocType", "Asset Settings"):
		frappe.reload_doctype("Asset Category")
		cwip_value = frappe.db.get_single_value("Asset Settings", "disable_cwip_accounting")
		
		frappe.db.sql("""UPDATE `tabAsset Category` SET enable_cwip_accounting = %s""", cint(cwip_value))

		frappe.db.sql("""DELETE FROM `tabSingles` where doctype = 'Asset Settings'""")
		frappe.delete_doc_if_exists("DocType", "Asset Settings")