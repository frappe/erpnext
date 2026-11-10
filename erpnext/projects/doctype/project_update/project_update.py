# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe.model.document import Document

from erpnext.deprecation_dumpster import project_update_daily_reminder, project_update_email_sending


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


daily_reminder = frappe.whitelist()(project_update_daily_reminder)
email_sending = project_update_email_sending
