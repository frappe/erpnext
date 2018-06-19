import frappe

def execute():
	if not frappe.db.exists("Party Type", "Student"):
		party = frappe.new_doc("Party Type")
		party.party_type = "Student"
		party.save()
