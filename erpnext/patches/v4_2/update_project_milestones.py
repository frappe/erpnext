import frappe

def execute():
	for project in frappe.db.sql_list("select name from tabProject"):
		p = frappe.get_doc("Project", project)
		p.update_milestones_completed()
		p.db_set("percent_milestones_completed", p.percent_milestones_completed)
