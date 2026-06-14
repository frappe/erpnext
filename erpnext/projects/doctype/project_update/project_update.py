# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document
from frappe.utils import add_days, today


class ProjectUpdate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.projects.doctype.project_user.project_user import ProjectUser

		amended_from: DF.Link | None
		date: DF.Date | None
		naming_series: DF.Data | None
		project: DF.Link
		sent: DF.Check
		time: DF.Time | None
		users: DF.Table[ProjectUser]
	# end: auto-generated types

	pass


@frappe.whitelist()
def daily_reminder():
	projects = frappe.get_all(
		"Project",
		fields=[
			"project_name",
			"frequency",
			"expected_start_date",
			"expected_end_date",
			"percent_complete",
		],
	)
	for project in projects:
		project_name = project.project_name
		frequency = project.frequency
		date_start = project.expected_start_date
		date_end = project.expected_end_date
		progress = project.percent_complete
		number_of_drafts = frappe.db.count("Project Update", {"project": project_name, "docstatus": 0})
		update = frappe.get_all(
			"Project Update",
			filters={"project": project_name, "date": add_days(today(), -1)},
			fields=["name", "date", "time", "progress", "progress_details"],
			as_list=True,
		)
		email_sending(project_name, frequency, date_start, date_end, progress, number_of_drafts, update)


def email_sending(project_name, frequency, date_start, date_end, progress, number_of_drafts, update):
	holiday_today = frappe.db.exists("Holiday", {"holiday_date": today()})
	msg = (
		"<p>Project Name: "
		+ project_name
		+ "</p><p>Frequency: "
		+ " "
		+ frequency
		+ "</p><p>Update Reminder:"
		+ " "
		+ str(date_start)
		+ "</p><p>Expected Date End:"
		+ " "
		+ str(date_end)
		+ "</p><p>Percent Progress:"
		+ " "
		+ str(progress)
		+ "</p><p>Number of Updates:"
		+ " "
		+ str(len(update))
		+ "</p>"
		+ "</p><p>Number of drafts:"
		+ " "
		+ str(number_of_drafts)
		+ "</p>"
	)
	msg += """</u></b></p><table class='table table-bordered'><tr>
                <th>Project ID</th><th>Date Updated</th><th>Time Updated</th><th>Project Status</th><th>Notes</th>"""
	for updates in update:
		msg += (
			"<tr><td>"
			+ str(updates[0])
			+ "</td><td>"
			+ str(updates[1])
			+ "</td><td>"
			+ str(updates[2])
			+ "</td><td>"
			+ str(updates[3])
			+ "</td>"
			+ "</td><td>"
			+ str(updates[4])
			+ "</td></tr>"
		)

	msg += "</table>"
	if not holiday_today:
		recipients = frappe.get_all("Project User", filters={"parent": project_name}, pluck="user")
		for user in recipients:
			frappe.sendmail(recipients=[user], subject=frappe._(project_name + " " + "Summary"), message=msg)
	else:
		pass
