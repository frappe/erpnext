from __future__ import unicode_literals
import frappe
from erpnext.healthcare.setup import setup_patient_history_settings

def execute():
	if "Healthcare" not in frappe.get_active_domains():
		return

	frappe.reload_doc("healthcare", "doctype", "Inpatient Medication Order")
	frappe.reload_doc("healthcare", "doctype", "Therapy Session")
	frappe.reload_doc("healthcare", "doctype", "Clinical Procedure")
	frappe.reload_doc("healthcare", "doctype", "Patient History Settings")
	frappe.reload_doc("healthcare", "doctype", "Patient History Standard Document Type")
	frappe.reload_doc("healthcare", "doctype", "Patient History Custom Document Type")

	setup_patient_history_settings()