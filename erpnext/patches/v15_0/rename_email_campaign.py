import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	"""
	Email Campaign was renamed to a more generic Campaign Run in order to
	accomodate more modes of communication in the future
	"""
	frappe.rename_doc("DocType", "Email Campaign", "Campaign Run", force=True)
	frappe.reload_doc("crm", "doctype", "campaign_run")
	rename_field("Campaign Run", "email_campaign_for", "campaign_run_for")
	frappe.rename_doc("DocType", "Campaign Email Schedule", "Campaign Schedule", force=True)
	frappe.reload_doc("crm", "doctype", "campaign_schedule")
