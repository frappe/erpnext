# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class SubProject(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.projects.doctype.project_user.project_user import ProjectUser
		from erpnext.projects.doctype.work_package_list.work_package_list import WorkPackageList
		from frappe.types import DF

		expected_end_date: DF.Date | None
		expected_start_date: DF.Date | None
		is_active: DF.Literal["Yes", "No"]
		notes: DF.TextEditor | None
		parent_project: DF.Link | None
		percent_complete: DF.Percent
		priority: DF.Literal["", "Medium", "Low", "High"]
		status: DF.Literal["Open", "Hold", "Completed", "Cancelled"]
		sub_project_name: DF.Data
		users: DF.Table[ProjectUser]
		work_packages: DF.Table[WorkPackageList]
	# end: auto-generated types


@frappe.whitelist()
def update_percent_complete(sp_name):
    sp = frappe.get_doc("Sub Project", sp_name)
    total_progress = 0
    count = 0
    for task in sp.work_packages:
	    if task.progress is not None:
	        total_progress += task.progress
	        count += 1

    # Calculate average
    avg_progress = total_progress / count if count > 0 else 0

    # Update parent Task progress
    # sp.percent_complete = avg_progress
    # sp.save(ignore_permissions=True)

    return avg_progress

@frappe.whitelist()
def get_work_packages(sub_project_name):
	wp = frappe.get_all("Work Packages", filters={"parent_sub_project" : sub_project_name}, fields=["name", "work_package_name", "progress"])
	return wp or []
