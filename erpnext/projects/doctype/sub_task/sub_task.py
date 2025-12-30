# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class SubTask(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from erpnext.projects.doctype.sub_task_people.sub_task_people import SubTaskPeople
		from frappe.types import DF

		completed_by: DF.Link | None
		completed_on: DF.Date | None
		description: DF.TextEditor | None
		expected_end_date: DF.Date | None
		expected_start_date: DF.Date | None
		expected_time_in_hours: DF.Float
		parent_task: DF.Link | None
		priority: DF.Literal["", "Low", "Medium", "High", "Urgent"]
		status: DF.Literal["Open", "Hold", "Completed"]
		sub_task_name: DF.Data
		task_progress: DF.Percent
		users: DF.Table[SubTaskPeople]
	# end: auto-generated types

	def validate(self):
		if self.task_progress is not None and self.task_progress > 100:
			frappe.throw("Task progress cannot be greater than 100")

	def on_update(self):
		task_name = frappe.db.get_value("Task", self.parent_task, "subject")
		old_doc = self.get_doc_before_save()

		new_users = set()
		old_users = set()

		if old_doc and old_doc.users:
			for mem in old_doc.users:
				if mem.assignee:
					old_users.add(mem.assignee)
				if mem.accountable:
					old_users.add(mem.accountable)

		if self.users:
			for mem in self.users:
				if mem.assignee:
					new_users.add(mem.assignee)
				if mem.accountable:
					new_users.add(mem.accountable)

		newly_added_users = new_users - old_users

		# --- Send mail for newly added users ---
		if newly_added_users:
			subject = f"New Sub Task Created: {self.sub_task_name} under {self.parent_task or 'No Parent Task'}"

			message = f"""
			<p>Dear User,</p>
			<p>You got a new <b>Sub Task</b></p>

			<table border="1" cellpadding="6" style="border-collapse:collapse;">
				<tr><th>Field</th><th>Details</th></tr>
				<tr><td><b>Sub Task</b></td><td>{self.sub_task_name}</td></tr>
                <tr><td><b>Sub Task ID</b></td><td>{self.name}</td></tr>
				<tr><td><b>Parent Task</b></td><td>{task_name or 'N/A'}</td></tr>
				<tr><td><b>Priority</b></td><td>{self.priority or 'Medium'}</td></tr>
				<tr><td><b>Status</b></td><td>{self.status or 'Open'}</td></tr>
			</table>

			<p>
			<a href="{frappe.utils.get_url()}/app/sub-task/{self.name}" target="_blank">
			Click here to view the Sub Task
			</a>
			</p>

			<p>Regards,<br><b>OTS</b></p>
			"""

			frappe.sendmail(
				recipients=list(newly_added_users),
				subject=subject,
				message=message,
			)

		# --- Send mail when Sub Task is completed ---
		if old_doc and old_doc.status != "Completed" and self.status == "Completed":
			recipients = set()
			if self.users:
				for user in self.users:
					if user.accountable:
						recipients.add(user.accountable)

				subject = f"Sub Task is Completed: {self.sub_task_name} under {self.parent_task or 'No Parent Task'}"
				message = f"""
				<p>Dear Accountable,</p>
				<p>Sub Task is Completed.</p>

				<table border="1" cellpadding="6" style="border-collapse:collapse;">
					<tr><th>Field</th><th>Details</th></tr>
					<tr><td><b>Sub Task</b></td><td>{self.sub_task_name}</td></tr>
                    <tr><td><b>Sub Task ID</b></td><td>{self.name}</td></tr>
					<tr><td><b>Parent Task</b></td><td>{task_name or 'N/A'}</td></tr>
				</table>

				<p>
				<a href="{frappe.utils.get_url()}/app/sub-task/{self.name}" target="_blank">
				Click here to view the Sub Task
				</a>
				</p>

				<p>Regards,<br><b>OTS</b></p>
				"""

				frappe.sendmail(
					recipients=list(recipients),
					subject=subject,
					message=message,
				)

		# --- Send mail when Sub Task is put on Hold ---
		if old_doc and old_doc.status != "Hold" and self.status == "Hold":
			recipients = set()
			if self.users:
				for user in self.users:
					if user.accountable:
						recipients.add(user.accountable)

				subject = f"Sub Task is kept on hold: {self.sub_task_name} under {self.parent_task or 'No Parent Task'}"
				message = f"""
				<p>Dear Accountable,</p>
				<p>Sub Task is kept on hold.</p>

				<table border="1" cellpadding="6" style="border-collapse:collapse;">
					<tr><th>Field</th><th>Details</th></tr>
					<tr><td><b>Sub Task</b></td><td>{self.sub_task_name}</td></tr>
                    <tr><td><b>Sub Task ID</b></td><td>{self.name}</td></tr>
					<tr><td><b>Parent Task</b></td><td>{task_name or 'N/A'}</td></tr>
				</table>

				<p>
				<a href="{frappe.utils.get_url()}/app/sub-task/{self.name}" target="_blank">
				Click here to view the Sub Task
				</a>
				</p>

				<p>Regards,<br><b>OTS</b></p>
				"""

				frappe.sendmail(
					recipients=list(recipients),
					subject=subject,
					message=message,
				)

		# --- Send mail when Sub Task dates are changed ---
		if (
		    not self.is_new()
		    and old_doc
		    and (
		        str(old_doc.expected_start_date) != str(self.expected_start_date)
		        or str(old_doc.expected_end_date) != str(self.expected_end_date)
		    )
		):
		    recipients = set()
		    if self.users:
		        for user in self.users:
		            if user.accountable:
		                recipients.add(user.accountable)

		    subject = f"Sub Task date is updated: {self.sub_task_name} under {self.parent_task or 'No Parent Task'}"
		    message = f"""
		    <p>Dear Accountable,</p>
		    <p>Sub Task date has been updated.</p>

		    <table border="1" cellpadding="6" style="border-collapse:collapse;">
		        <tr><th>Field</th><th>Details</th></tr>
		        <tr><td><b>Sub Task</b></td><td>{self.sub_task_name}</td></tr>
                <tr><td><b>Sub Task ID</b></td><td>{self.name}</td></tr>
		        <tr><td><b>Parent Task</b></td><td>{task_name or 'N/A'}</td></tr>
		    </table>

		    <p>
		    <a href="{frappe.utils.get_url()}/app/sub-task/{self.name}" target="_blank">
		    Click here to view the Sub Task
		    </a>
		    </p>

		    <p>Regards,<br><b>OTS</b></p>
		    """

		    frappe.sendmail(
		        recipients=list(recipients),
		        subject=subject,
		        message=message,
		    )

