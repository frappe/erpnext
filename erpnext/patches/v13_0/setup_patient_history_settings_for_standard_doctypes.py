from __future__ import unicode_literals
import frappe
from erpnext.healthcare.setup import setup_patient_history_settings

def execute():
	if 'Healthcare' not in frappe.get_active_domains():
		return

	setup_patient_history_settings()