import frappe


def execute():
	frappe.reload_doc("hr", "doctype", "training_event")
	frappe.reload_doc("hr", "doctype", "training_event_employee")

	frappe.db.sql("update `tabTraining Event Employee` set `attendance` = 'Present'")
	frappe.db.sql(
		"update `tabTraining Event Employee` set `is_mandatory` = 1 where `attendance` = 'Mandatory'"
	)
