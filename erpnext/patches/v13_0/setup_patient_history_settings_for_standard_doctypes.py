from __future__ import unicode_literals
import frappe
from erpnext.healthcare.setup import setup_patient_history_settings

def execute():
	if "Healthcare" not in frappe.get_active_domains():
		return

	frappe.reload_doc("healthcare", "doctype", "Patient History Settings")
	frappe.reload_doc("healthcare", "doctype", "Patient History Standard Document Type")
	frappe.reload_doc("healthcare", "doctype", "Patient History Custom Document Type")

	setup_patient_history_settings()