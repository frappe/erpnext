import frappe
from frappe.utils import flt


def execute():
	for project in frappe.get_all("Project", fields=["name", "percent_complete_method"]):
		total = frappe.db.count("Task", dict(project=project.name))
		if project.percent_complete_method == "Task Completion" and total > 0:
			completed = frappe.db.count(
				"Task", {"project": project.name, "status": ["in", ["Cancelled", "Completed"]]}
			)
			percent_complete = flt(flt(completed) / total * 100, 2)
			if project.percent_complete != percent_complete:
				frappe.db.set_value("Project", project.name, "percent_complete", percent_complete)
				if percent_complete == 100:
					frappe.db.set_value("Project", project.name, "status", "Completed")
