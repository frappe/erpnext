import frappe
from erpnext.regional.india.setup import make_custom_fields

def execute():
	if frappe.db.exists("Company", {"country": "India"}):
		make_custom_fields()
