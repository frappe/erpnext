import frappe

def execute():
	frappe.reload_doc("support", "doctype", "issue_priority")

	priorities = frappe.get_meta("Issue").get_field("priority").options.split("\n")

	for priority in priorities:
		frappe.get_doc({
			"doctype": "Issue Priority",
			"name":priority
		}).insert(ignore_permissions=True)

	frappe.reload_doc("support", "doctype", "issue")

	for issue in frappe.get_list("Issue", fields=["name", "priority"]):
		frappe.db.set_value("Issue", issue.name, "priority", issue.priority)