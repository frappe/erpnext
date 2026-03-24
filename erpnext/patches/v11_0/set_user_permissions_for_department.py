import frappe


def execute():
	user_permissions = frappe.get_all(
		"User Permission", filters={"allow": "Department"}, fields=["name", "for_value"]
	)
	for d in user_permissions:
		user_permission = frappe.get_doc("User Permission", d.name)
		for new_dept in frappe.get_all(
			"Department",
			filters={"company": ["!=", ""], "department_name": d.for_value},
			pluck="name",
		):
			try:
				new_user_permission = frappe.copy_doc(user_permission)
				new_user_permission.for_value = new_dept
				new_user_permission.save()
			except frappe.DuplicateEntryError:
				pass

	frappe.reload_doc("hr", "doctype", "department")
	frappe.db.set_value("Department", {"company": ["in", ["", None]]}, "disabled", 1, update_modified=False)
