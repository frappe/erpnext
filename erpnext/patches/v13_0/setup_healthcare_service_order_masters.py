
from __future__ import unicode_literals
import frappe
from erpnext.healthcare.setup import setup_healthcare_service_order_masters

def execute():
	if "Healthcare" not in frappe.get_active_domains():
		return

	setup_healthcare_service_order_masters()