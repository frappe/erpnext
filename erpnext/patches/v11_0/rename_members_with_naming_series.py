import frappe

def execute():
	old_named_members = frappe.get_all("Member", filters = {"name": ("not like", "MEM-%")})
	correctly_named_members = frappe.get_all("Member", filters = {"name": ("like", "MEM-%")})
	current_index = len(correctly_named_members)

	for member in old_named_members:
		current_index += 1
		frappe.rename_doc("Member", member["name"], "MEM-" + str(current_index).zfill(5))
