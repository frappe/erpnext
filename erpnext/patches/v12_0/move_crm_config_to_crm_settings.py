import frappe

def execute():
	frappe.reload_doc("crm", "doctype", "crm_settings")

	fields_to_move = ["campaign_naming_by", "close_opportunity_after_days"]

	for field in fields_to_move:
		value = frappe.db.get_value("Selling Settings", None, field)
		frappe.db.set_value("CRM Settings", "CRM Settings", field, value, update_modified=False)
