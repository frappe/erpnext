import frappe

def execute():
	# convert milestones to tasks
	frappe.reload_doctype("Project")

	for m in frappe.get_all("Project Milestone", "*"):
		if (m.milestone and m.milestone_date
			and frappe.db.exists("Project", m.parent)):
			frappe.get_doc({
				"doctype": "Task",
				"subject": m.milestone,
				"expected_start_date": m.milestone_date,
				"status": "Open" if m.status=="Pending" else "Closed",
				"project": m.parent,
			}).insert(ignore_permissions=True)

	# remove project milestone
	frappe.delete_doc("DocType", "Project Milestone")

	# remove calendar events for milestone
	for e in frappe.get_all("Event", ["name"], {"ref_type": "Project"}):
		frappe.delete_doc("Event", e.name)
