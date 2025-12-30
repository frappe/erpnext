# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class WorkPackages(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.projects.doctype.project_user.project_user import ProjectUser
		from erpnext.projects.doctype.task_depends_on.task_depends_on import TaskDependsOn
		from frappe.types import DF

		expected_end_date: DF.Date | None
		expected_start_date: DF.Date | None
		is_active: DF.Literal["Yes", "No"]
		module: DF.Data | None
		notes: DF.TextEditor | None
		parent_project: DF.Link | None
		parent_sub_project: DF.Link | None
		priority: DF.Literal["", "High", "Medium", "Low"]
		progress: DF.Percent
		tasks: DF.Table[TaskDependsOn]
		users: DF.Table[ProjectUser]
		work_package_name: DF.Data
	# end: auto-generated types
	


@frappe.whitelist()
def update_percent_complete(wp_name):
    wp = frappe.get_doc("Work Packages", wp_name)
    total_progress = 0
    count = 0
    for task in wp.tasks:
	    if task.progress is not None:
	        total_progress += task.progress
	        count += 1

    # Calculate average
    avg_progress = total_progress / count if count > 0 else 0

    # Update parent Task progress
    # wp.progress = avg_progress
    # wp.save(ignore_permissions=True)

    return avg_progress

@frappe.whitelist()
def get_tasks(wp_name):
    tasks = frappe.db.get_all(
        "Task",
        filters={"work_package_name": wp_name},
        fields=["name", "subject", "progress"]
    )
    return tasks or []
