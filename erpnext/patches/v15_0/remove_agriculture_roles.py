import frappe


def execute():
	if "agriculture" in frappe.get_installed_apps():
		return

	for role in ["Agriculture User", "Agriculture Manager"]:
		assignments = frappe.get_all("Has Role", {"role": role}, pluck="name")
		for assignment in assignments:
			frappe.delete_doc("Has Role", assignment, ignore_missing=True, force=True)
		frappe.delete_doc("Role", role, ignore_missing=True, force=True)
