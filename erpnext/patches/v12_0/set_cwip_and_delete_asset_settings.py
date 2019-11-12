from __future__ import unicode_literals
import frappe
from frappe.utils import cint


def execute():
	'''Get 'Disable CWIP Accounting value' from Asset Settings, set it in 'Enable Capital Work in Progress Accounting' field
	in Company, delete Asset Settings '''

	if frappe.db.exists("DocType","Asset Settings"):
		frappe.reload_doctype("Company")
		cwip_value = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE doctype='Asset Settings'
			and field='disable_cwip_accounting' """, as_dict=1)

		companies = [x['name'] for x in frappe.get_all("Company", "name")]
		for company in companies:
			enable_cwip_accounting = cint(not cint(cwip_value[0]['value']))
			frappe.set_value("Company", company, "enable_cwip_accounting", enable_cwip_accounting)

		frappe.db.sql(
			""" DELETE FROM `tabSingles` where doctype = 'Asset Settings' """)
		frappe.delete_doc_if_exists("DocType","Asset Settings")