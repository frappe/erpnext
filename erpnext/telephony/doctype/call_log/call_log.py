# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.contacts.doctype.contact.contact import get_contact_with_phone_number
from frappe.core.doctype.dynamic_link.dynamic_link import deduplicate_dynamic_links
from frappe.model.document import Document

from erpnext.crm.doctype.lead.lead import get_lead_with_phone_number
from erpnext.crm.doctype.utils import get_scheduled_employees_for_popup, strip_number

END_CALL_STATUSES = ["No Answer", "Completed", "Busy", "Failed"]
ONGOING_CALL_STATUSES = ["Ringing", "In Progress"]


class CallLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.core.doctype.dynamic_link.dynamic_link import DynamicLink
		from frappe.types import DF

		call_received_by: DF.Link | None
		customer: DF.Link | None
		duration: DF.Duration | None
		employee_user_id: DF.Link | None
		end_time: DF.Datetime | None
		id: DF.Data | None
		links: DF.Table[DynamicLink]
		medium: DF.Data | None
		recording_url: DF.Data | None
		start_time: DF.Datetime | None
		status: DF.Literal[
			"Ringing", "In Progress", "Completed", "Failed", "Busy", "No Answer", "Queued", "Canceled"
		]
		summary: DF.SmallText | None
		to: DF.Data | None
		type: DF.Literal["Incoming", "Outgoing"]
		type_of_call: DF.Link | None
	# end: auto-generated types

	def validate(self):
		deduplicate_dynamic_links(self)

	def before_insert(self):
		"""Add lead(third party person) links to the document."""
		lead_number = self.get("from") if self.is_incoming_call() else self.get("to")
		lead_number = strip_number(lead_number)

		if contact := get_contact_with_phone_number(strip_number(lead_number)):
			self.add_link(link_type="Contact", link_name=contact)

		if lead := get_lead_with_phone_number(lead_number):
			self.add_link(link_type="Lead", link_name=lead)

		# Add Employee Name
		if self.is_incoming_call():
			self.update_received_by()

	def after_insert(self):
		self.trigger_call_popup()

	def on_update(self):
		def _is_call_missed(doc_before_save, doc_after_save):
			# FIXME: This works for Exotel but not for all telepony providers
			return doc_before_save.to != doc_after_save.to and doc_after_save.status not in END_CALL_STATUSES

		def _is_call_ended(doc_before_save, doc_after_save):
			return doc_before_save.status not in END_CALL_STATUSES and self.status in END_CALL_STATUSES

		doc_before_save = self.get_doc_before_save()
		if not doc_before_save:
			return

		if self.is_incoming_call() and self.has_value_changed("to"):
			self.update_received_by()

		if _is_call_missed(doc_before_save, self):
			frappe.publish_realtime(f"call_{self.id}_missed", self)
			self.trigger_call_popup()

		if _is_call_ended(doc_before_save, self):
			frappe.publish_realtime(f"call_{self.id}_ended", self)

	def is_incoming_call(self):
		return self.type == "Incoming"

	def add_link(self, link_type, link_name):
		self.append("links", {"link_doctype": link_type, "link_name": link_name})

	def trigger_call_popup(self):
		if not self.is_incoming_call():
			return

		scheduled_employees = get_scheduled_employees_for_popup(self.medium)
		employees = get_employees_with_number(self.to)
		employee_emails = [employee.get("user_id") for employee in employees]

		# check if employees with matched number are scheduled to receive popup
		emails = set(scheduled_employees).intersection(employee_emails)

		if frappe.conf.developer_mode:
			self.add_comment(
				text=f"""
					Scheduled Employees: {scheduled_employees}
					Matching Employee: {employee_emails}
					Show Popup To: {emails}
				"""
			)

		if employee_emails and not emails:
			self.add_comment(text=_("No employee was scheduled for call popup"))

		for email in emails:
			frappe.publish_realtime("show_call_popup", self, user=email)

	def update_received_by(self):
		if employees := get_employees_with_number(self.get("to")):
			self.call_received_by = employees[0].get("name")
			self.employee_user_id = employees[0].get("user_id")


@frappe.whitelist()
def add_call_summary_and_call_type(call_log, summary, call_type):
	doc = frappe.get_doc("Call Log", call_log)
	doc.type_of_call = call_type
	doc.save()
	doc.add_comment("Comment", frappe.bold(_("Call Summary")) + "<br><br>" + summary)


def get_employees_with_number(number):
	number = strip_number(number)
	if not number:
		return []

	employee_doc_name_and_emails = frappe.cache().hget("employees_with_number", number)
	if employee_doc_name_and_emails:
		return employee_doc_name_and_emails

	employee_doc_name_and_emails = frappe.get_all(
		"Employee",
		filters={"cell_number": ["like", f"%{number}%"], "user_id": ["!=", ""]},
		fields=["name", "user_id"],
	)

	frappe.cache().hset("employees_with_number", number, employee_doc_name_and_emails)

	return employee_doc_name_and_emails


def link_existing_conversations(doc, state):
	"""
	Called from hooks on creation of Contact or Lead to link all the existing conversations.
	"""
	if doc.doctype != "Contact":
		return
	try:
		numbers = [d.phone for d in doc.phone_nos]

		for number in numbers:
			number = strip_number(number)
			if not number:
				continue
			logs = frappe.db.sql_list(
				"""
				SELECT cl.name FROM `tabCall Log` cl
				LEFT JOIN `tabDynamic Link` dl
				ON cl.name = dl.parent
				WHERE (cl.`from` like %(phone_number)s or cl.`to` like %(phone_number)s)
				GROUP BY cl.name
				HAVING SUM(
					CASE
						WHEN dl.link_doctype = %(doctype)s AND dl.link_name = %(docname)s
						THEN 1
						ELSE 0
					END
				)=0
				""",
				dict(phone_number=f"%{number}", docname=doc.name, doctype=doc.doctype),
			)

			for log in logs:
				call_log = frappe.get_doc("Call Log", log)
				call_log.add_link(link_type=doc.doctype, link_name=doc.name)
				call_log.save(ignore_permissions=True)
			frappe.db.commit()
	except Exception:
		frappe.log_error(title=_("Error during caller information update"))


def get_linked_call_logs(doctype, docname):
	# content will be shown in timeline
	logs = frappe.get_all(
		"Dynamic Link",
		fields=["parent"],
		filters={"parenttype": "Call Log", "link_doctype": doctype, "link_name": docname},
	)

	logs = {log.parent for log in logs}

	logs = frappe.get_all("Call Log", fields=["*"], filters={"name": ["in", logs]})

	timeline_contents = []
	for log in logs:
		log.show_call_button = 0
		timeline_contents.append(
			{
				"icon": "call",
				"is_card": True,
				"creation": log.creation,
				"template": "call_link",
				"template_data": log,
			}
		)

	return timeline_contents
