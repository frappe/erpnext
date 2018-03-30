import frappe

def execute():
	frappe.reload_doctype("Project")
	frappe.db.sql("update `tabProject` set expected_start_date = project_start_date, \
		expected_end_date = completion_date, actual_end_date = act_completion_date, \
		estimated_costing = project_value, gross_margin = gross_margin_value")