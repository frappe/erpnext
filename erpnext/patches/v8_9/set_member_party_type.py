import frappe

def execute():
	if not frappe.db.exists("Party Type", "Member"):
		party = frappe.new_doc("Party Type")
		party.party_type = "Member"
		party.save()
