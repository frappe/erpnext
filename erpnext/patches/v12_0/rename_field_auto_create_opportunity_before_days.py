from __future__ import unicode_literals
import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	frappe.reload_doc("crm", "doctype", "crm_settings")
	rename_field("CRM Settings", "auto_create_opportunity_before_days", "maintenance_opportunity_reminder_days")