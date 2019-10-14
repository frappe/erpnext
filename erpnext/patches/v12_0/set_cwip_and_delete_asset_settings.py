from __future__ import unicode_literals
import frappe
from frappe.utils import cint


def execute():
	'''Get Disable CWIP Accounting value from Asset Settings, set it in Enable Capital Work in Progress Accounting field
		in Company, delete Asset Settings '''

	cwip_value = frappe.db.sql(""" SELECT value FROM `tabSingles` WHERE doctype='Asset Settings'
		and field='disable_cwip_accounting' """, as_dict=1)
	company = frappe.db.get_single_value("Global Defaults", "default_company")

	if company:
		company_doc = frappe.get_doc("Company", company)
		company_doc.enable_cwip_accounting = cint(not cint(cwip_value[0]['value']))
		company_doc.save()
	else:
		companies = [x['name'] for x in frappe.get_all("Company", "name")]
		for company in companies:
			company_doc = frappe.get_doc("Company", company)
			company_doc.enable_cwip_accounting = cint(not cint(cwip_value[0]['value']))
			company_doc.save()

	frappe.db.sql(
		""" DELETE FROM `tabSingles` where doctype = 'Asset Settings' """)
