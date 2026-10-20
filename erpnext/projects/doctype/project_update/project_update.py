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
	# This endpoint emails every Project User across every Project, so restrict it to managers.
	frappe.only_for("Projects Manager")

	# Same for every project this run, so check once instead of once per project.
	holiday_today = frappe.db.exists("Holiday", {"holiday_date": today()})

	projects = frappe.get_all(
		"Project",
		fields=[
			"name",
			"project_name",
			"frequency",
			"expected_start_date",
			"expected_end_date",
			"percent_complete",
		],
		limit_page_length=0,  # intentionally unbounded: every project is reminded
	)
	for project in projects:
		# project.name is the document key (e.g. PROJ-0001); Project Update.project and the
		# Project User child rows store it, NOT the project_name display value.
		project_id = project.name
		frequency = project.frequency
		date_start = project.expected_start_date
		date_end = project.expected_end_date
		progress = project.percent_complete
		number_of_drafts = frappe.db.count("Project Update", {"project": project_id, "docstatus": 0})
		# "progress"/"progress_details" are not fields on Project Update (selecting them errored on
		# both engines); report the columns that actually exist.
		update = frappe.get_all(
			"Project Update",
			filters={"project": project_id, "date": add_days(today(), -1)},
			fields=["name", "date", "time"],
			as_list=True,
		)
		email_sending(
			project_id,
			project.project_name,
			frequency,
			date_start,
			date_end,
			progress,
			number_of_drafts,
			update,
			holiday_today,
		)


def email_sending(
	project_id,
	project_name,
	frequency,
	date_start,
	date_end,
	progress,
	number_of_drafts,
	update,
	holiday_today,
):
	msg = (
		"<p>Project Name: "
		+ project_name
		+ "</p><p>Frequency: "
		+ " "
		+ str(frequency)
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
                <th>Project ID</th><th>Date Updated</th><th>Time Updated</th></tr>"""
	for updates in update:
		msg += (
			"<tr><td>"
			+ str(updates[0])
			+ "</td><td>"
			+ str(updates[1])
			+ "</td><td>"
			+ str(updates[2])
			+ "</td></tr>"
		)

	msg += "</table>"
	if not holiday_today:
		recipients = frappe.get_all(
			"Project User",
			filters={"parent": project_id},
			pluck="user",
			limit_page_length=0,  # every project member must be reminded, not just the first page
		)
		for user in recipients:
			frappe.sendmail(recipients=[user], subject=frappe._(project_name + " " + "Summary"), message=msg)
	else:
		pass
