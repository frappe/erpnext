from __future__ import unicode_literals
import frappe

def execute():
	company = frappe.db.get_single_value('Global Defaults', 'default_company')
	doctypes = ['Clinical Procedure', 'Inpatient Record', 'Lab Test', 'Patient Appointment', 'Patient Encounter', 'Vital Signs']
	for entry in doctypes:
		if frappe.db.exists('DocType', entry):
			frappe.reload_doc("Healthcare", "doctype", entry)
			frappe.db.sql("update `tab{dt}` set company = '{company}' where ifnull(company, '') = ''".format(dt=entry, company=company))
