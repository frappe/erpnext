import frappe

def execute():
	if not frappe.db.exists("Party Type", "Member"):
		frappe.reload_doc("non_profit", "doctype", "member")
		party = frappe.new_doc("Party Type")
		party.party_type = "Member"
		party.save()
