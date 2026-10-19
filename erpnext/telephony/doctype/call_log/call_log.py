# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.core.doctype.dynamic_link.dynamic_link import deduplicate_dynamic_links
from frappe.model.document import Document
from frappe.query_builder import Case
from frappe.query_builder.functions import Sum

from erpnext.crm.doctype.lead.lead import get_leads_with_phone_number
from erpnext.crm.doctype.utils import (
	get_contacts_with_phone_number,
	get_phone_number_key,
	get_phone_number_like_pattern,
	get_scheduled_employees_for_popup,
)

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
			"Ringing", "In Progress", "Completed", "Failed", "Busy", "No Answer", "Queued", "Cancelled"
		]
		summary: DF.SmallText | None
		to: DF.Data | None
		type: DF.Literal["Incoming", "Outgoing"]
		type_of_call: DF.Link | None
	# end: auto-generated types

	def validate(self):
		deduplicate_dynamic_links(self)
		if not self.is_new() and self.is_incoming_call() and self.has_value_changed("to"):
			self.update_received_by()

	def before_insert(self):
		"""Add links to all contacts and leads (third party person) with the caller's number."""
		number = self.get("from") if self.is_incoming_call() else self.get("to")

		for contact in get_contacts_with_phone_number(number):
			self.add_link(link_type="Contact", link_name=contact)
			self.link_customer_of_contact(contact)

		for lead in get_leads_with_phone_number(number):
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

		if _is_call_missed(doc_before_save, self):
			self.notify_call_agents(doc_before_save, "missed")
			self.trigger_call_popup()

		if _is_call_ended(doc_before_save, self):
			self.notify_call_agents(doc_before_save, "ended")

	def notify_call_agents(self, doc_before_save: "CallLog", event: str):
		# Skip the schedule check: an agent whose slot ended mid-call must still close the popup.
		for email in doc_before_save.get_agent_emails():
			frappe.publish_realtime(f"call_{self.id}_{event}", self, user=email)

	def is_incoming_call(self):
		return self.type == "Incoming"

	def add_link(self, link_type, link_name):
		self.append("links", {"link_doctype": link_type, "link_name": link_name})

	def link_customer_of_contact(self, contact: str):
		customer = frappe.db.get_value(
			"Dynamic Link",
			{"parenttype": "Contact", "parent": contact, "link_doctype": "Customer"},
			"link_name",
		)
		if customer:
			self.customer = self.customer or customer
			self.add_link(link_type="Customer", link_name=customer)

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

	def get_agent_emails(self) -> set[str]:
		if not self.is_incoming_call():
			return set()

		return {employee.get("user_id") for employee in get_employees_with_number(self.to)}

	def update_received_by(self):
		if employees := get_employees_with_number(self.get("to")):
			self.call_received_by = employees[0].get("name")
			self.employee_user_id = employees[0].get("user_id")


@frappe.whitelist(methods=["POST"])
def add_call_summary_and_call_type(call_log: str, summary: str, call_type: str | None = None):
	validate_call_type(call_type)
	doc = frappe.get_doc("Call Log", call_log)
	doc.check_permission("read")
	# the agent who took the call may record its summary without write access
	if doc.employee_user_id != frappe.session.user:
		doc.check_permission("write")

	if call_type:
		doc.type_of_call = call_type
	doc.summary = summary
	doc.save(ignore_permissions=True)
	doc.add_comment("Comment", frappe.bold(_("Call Summary")) + "<br><br>" + summary)


def validate_call_type(call_type: str | None):
	if call_type and frappe.db.get_value("Telephony Call Type", call_type, "docstatus") != 1:
		frappe.throw(_("Call Type {0} is not submitted.").format(frappe.bold(call_type)))


def get_employees_with_number(number):
	key = get_phone_number_key(number)
	if not key:
		return []

	employee_doc_name_and_emails = frappe.cache().hget("employees_with_number", key)
	if employee_doc_name_and_emails:
		return employee_doc_name_and_emails

	employees = frappe.get_all(
		"Employee",
		filters={"cell_number": ["like", get_phone_number_like_pattern(key)], "user_id": ["!=", ""]},
		fields=["name", "user_id", "cell_number"],
	)
	employee_doc_name_and_emails = [
		frappe._dict(name=employee.name, user_id=employee.user_id)
		for employee in employees
		if get_phone_number_key(employee.cell_number) == key
	]

	frappe.cache().hset("employees_with_number", key, employee_doc_name_and_emails)

	return employee_doc_name_and_emails


def link_existing_conversations(doc, state):
	"""
	Called from hooks on update of Contact or Lead to link the existing conversations of new numbers.
	"""
	if doc.flags.ignore_auto_link_call_log:
		return
	numbers = get_new_phone_numbers(doc)
	if not numbers:
		return
	frappe.db.savepoint("link_call_logs")
	try:
		for number in numbers:
			for log in get_unlinked_call_logs_with_number(doc, number):
				call_log = frappe.get_doc("Call Log", log)
				call_log.add_link(link_type=doc.doctype, link_name=doc.name)
				if doc.doctype == "Contact" and not call_log.customer:
					call_log.link_customer_of_contact(doc.name)
				call_log.save(ignore_permissions=True)
	except Exception:
		frappe.db.rollback(save_point="link_call_logs")
		frappe.log_error(title=_("Error during caller information update"))


def get_unlinked_call_logs_with_number(doc, number: str) -> list[str]:
	"""Return call logs from or to the number that are not yet linked to the document."""
	if not (key := get_phone_number_key(number)):
		return []

	pattern = get_phone_number_like_pattern(key)
	call_log = frappe.qb.DocType("Call Log")
	dynamic_link = frappe.qb.DocType("Dynamic Link")
	logs = (
		frappe.qb.from_(call_log)
		.left_join(dynamic_link)
		.on(call_log.name == dynamic_link.parent)
		.select(call_log.name, call_log["from"], call_log["to"])
		.where(call_log["from"].like(pattern) | call_log["to"].like(pattern))
		.groupby(call_log.name, call_log["from"], call_log["to"])
		.having(
			Sum(
				Case()
				.when((dynamic_link.link_doctype == doc.doctype) & (dynamic_link.link_name == doc.name), 1)
				.else_(0)
			)
			== 0
		)
		.run(as_dict=True)
	)
	return [
		log.name for log in logs if key in (get_phone_number_key(log["from"]), get_phone_number_key(log.to))
	]


def get_new_phone_numbers(doc) -> set[str]:
	numbers = set(get_phone_numbers(doc))
	if doc_before_save := doc.get_doc_before_save():
		numbers -= set(get_phone_numbers(doc_before_save))
	return numbers


def get_phone_numbers(doc) -> list[str]:
	if doc.doctype == "Contact":
		numbers = [d.phone for d in doc.phone_nos]
	else:
		numbers = [doc.get("phone"), doc.get("mobile_no")]
	return [number for number in numbers if number]


def get_linked_call_logs(doctype, docname):
	# content will be shown in timeline
	if not frappe.has_permission("Call Log", "read"):
		return []

	logs = frappe.get_all(
		"Dynamic Link",
		fields=["parent"],
		filters={"parenttype": "Call Log", "link_doctype": doctype, "link_name": docname},
	)
	if not logs:
		return []

	logs = {log.parent for log in logs}

	logs = frappe.get_list(
		"Call Log",
		fields=["name", "type", "from", "to", "duration", "summary", "recording_url", "creation"],
		filters={"name": ["in", logs]},
	)

	timeline_contents = []
	for log in logs:
		log.show_call_button = 0
		timeline_contents.append(
			{
				"icon": "phone",
				"is_card": True,
				"creation": log.creation,
				"template": "call_link",
				"template_data": log,
			}
		)

	return timeline_contents
