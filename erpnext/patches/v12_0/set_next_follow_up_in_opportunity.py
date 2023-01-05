import frappe

def execute():
	frappe.reload_doc("crm", "doctype", "opportunity")
	opp_list = frappe.get_all("Opportunity")

	for opp in opp_list:
		doc = frappe.get_doc("Opportunity", opp)
		doc.db_set('next_follow_up', doc.get_next_follow_up_date(), update_modified=False)
		doc.set_title()
		doc.db_set('title', doc.title, update_modified=False)
		doc.clear_cache()
