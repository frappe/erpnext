# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from datetime import date

import frappe
from frappe import _
from frappe.core.doctype.communication.email import make
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today


class EmailCampaign(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		campaign_name: DF.Link
		email_campaign_for: DF.Literal["", "Lead", "Contact", "Email Group"]
		end_date: DF.Date | None
		recipient: DF.DynamicLink
		sender: DF.Link | None
		start_date: DF.Date
		status: DF.Literal["", "Scheduled", "In Progress", "Completed", "Unsubscribed"]
	# end: auto-generated types

	def validate(self):
		self.set_date()
		self.validate_recipient_email()
		self.validate_email_campaign_already_exists()
		self.update_status()

	def validate_recipient_email(self):
		if not self.recipient:
			return

		if self.email_campaign_for == "Lead":
			self.validate_lead()
		elif self.email_campaign_for == "Contact":
			self.validate_contact()

	def set_date(self):
		start_date_changed = self.is_new() or self.has_value_changed("start_date")
		if start_date_changed and getdate(self.start_date) < getdate(today()):
			frappe.throw(_("Start Date cannot be before the current date"))

		self.end_date = self.get_end_date()
		if not self.end_date:
			frappe.throw(
				_("Please set up the Campaign Schedule in the Campaign {0}").format(self.campaign_name)
			)

	def get_end_date(self) -> date | None:
		"""Return start date + the longest send after days in the Campaign's current schedule."""
		campaign = frappe.get_cached_doc("Campaign", self.campaign_name)
		send_after_days = [entry.send_after_days for entry in campaign.get("campaign_schedules")]
		if send_after_days:
			return add_days(getdate(self.start_date), max(send_after_days))

	def refresh_end_date(self):
		end_date = self.get_end_date()
		if end_date and end_date != getdate(self.end_date):
			self.db_set("end_date", end_date, update_modified=False)

	def validate_lead(self):
		lead = frappe.db.get_value(
			"Lead", self.recipient, ["email_id", "lead_name", "unsubscribed"], as_dict=True
		)
		if not lead.email_id:
			frappe.throw(_("Please set an email id for the Lead {0}").format(lead.lead_name))
		self.validate_not_unsubscribed(lead)

	def validate_contact(self):
		contact = frappe.db.get_value(
			"Contact", self.recipient, ["email_id", "full_name", "unsubscribed"], as_dict=True
		)
		if contact and not contact.email_id:
			frappe.throw(
				_("Please set a primary email ID for the Contact {0}").format(frappe.bold(contact.full_name))
			)
		self.validate_not_unsubscribed(contact)

	def validate_not_unsubscribed(self, recipient: dict | None):
		if self.is_new() and recipient and recipient.unsubscribed:
			frappe.throw(
				_("{0} {1} has unsubscribed from emails").format(
					_(self.email_campaign_for), frappe.bold(self.recipient)
				)
			)

	def validate_email_campaign_already_exists(self):
		email_campaign_exists = frappe.db.exists(
			"Email Campaign",
			{
				"campaign_name": self.campaign_name,
				"recipient": self.recipient,
				"status": ("in", ["In Progress", "Scheduled"]),
				"name": ("!=", self.name),
			},
		)
		if email_campaign_exists:
			frappe.throw(
				_("The Campaign '{0}' already exists for the {1} '{2}'").format(
					self.campaign_name, self.email_campaign_for, self.recipient
				)
			)

	def update_status(self):
		if self.status == "Unsubscribed":
			return

		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)
		today_date = getdate(today())

		if start_date > today_date:
			new_status = "Scheduled"
		elif end_date >= today_date:
			new_status = "In Progress"
		else:
			new_status = "Completed"

		if self.status != new_status:
			self.db_set("status", new_status, update_modified=False)


# called through hooks to send campaign mails to leads
def send_email_to_leads_or_contacts():
	today_date = getdate(today())

	# Refresh end dates first, so steps added to a Campaign since the last status run are not missed
	set_email_campaign_status()
	email_campaigns = frappe.get_all(
		"Email Campaign",
		filters={
			"status": ("!=", "Unsubscribed"),
			"start_date": ("<=", today_date),
			"end_date": (">=", today_date),
		},
		fields=["name", "campaign_name", "email_campaign_for", "recipient", "start_date", "sender"],
	)

	if not email_campaigns:
		return

	# Process each email campaign
	for email_campaign in email_campaigns:
		try:
			campaign = frappe.get_cached_doc("Campaign", email_campaign.campaign_name)
		except frappe.DoesNotExistError:
			frappe.log_error(
				title=_("Email Campaign Error"),
				message=_("Campaign {0} not found").format(email_campaign.campaign_name),
			)
			continue

		# Find schedules that match today
		for entry in campaign.get("campaign_schedules"):
			try:
				scheduled_date = add_days(getdate(email_campaign.start_date), entry.get("send_after_days"))
				if scheduled_date == today_date and not is_step_sent(email_campaign.name, entry, today_date):
					send_mail(entry, email_campaign)
			except Exception:
				frappe.log_error(
					title=_("Email Campaign Send Error"),
					message=_("Failed to send email for campaign {0} to {1}").format(
						email_campaign.name, email_campaign.recipient
					),
				)


def is_step_sent(email_campaign: str, entry: Document, on_date: date) -> bool:
	return bool(
		frappe.db.exists(
			"Communication",
			{
				"reference_doctype": "Email Campaign",
				"reference_name": email_campaign,
				"email_template": entry.get("email_template"),
				"communication_date": (">=", on_date),
			},
		)
	)


def send_mail(entry, email_campaign):
	campaign_for = email_campaign.get("email_campaign_for")
	recipient = email_campaign.get("recipient")
	sender_user = email_campaign.get("sender")
	campaign_name = email_campaign.get("name")

	# Get recipient emails
	if campaign_for == "Email Group":
		recipient_list = frappe.get_all(
			"Email Group Member",
			filters={"email_group": recipient, "unsubscribed": 0},
			pluck="email",
		)
	else:
		email_id, unsubscribed = frappe.db.get_value(campaign_for, recipient, ["email_id", "unsubscribed"])
		if not email_id:
			frappe.log_error(
				title=_("Email Campaign Error"),
				message=_("No email found for {0} {1}").format(campaign_for, recipient),
			)
			return
		if unsubscribed:
			frappe.log_error(
				title=_("Email Campaign Error"),
				message=_("{0} {1} has unsubscribed from emails").format(campaign_for, recipient),
			)
			return
		recipient_list = [email_id]

	if not recipient_list:
		frappe.log_error(
			title=_("Email Campaign Error"),
			message=_("No recipients found for campaign {0}").format(campaign_name),
		)
		return

	# Get email template and sender
	email_template = frappe.get_cached_doc("Email Template", entry.get("email_template"))
	sender = frappe.db.get_value("User", sender_user, "email") if sender_user else None

	# Support both {{ doc.field }} and {{ field }}, as the Email Template help shows
	doc = frappe.get_doc(campaign_for, recipient)
	context = {**doc.as_dict(), "doc": doc}

	# Render template
	subject = frappe.render_template(email_template.get("subject"), context, restrict_globals=True)
	content = frappe.render_template(email_template.response_, context, restrict_globals=True)

	frappe.db.savepoint("email_campaign_send")
	try:
		comm = make(
			doctype="Email Campaign",
			name=campaign_name,
			subject=subject,
			content=content,
			sender=sender,
			recipients=recipient_list,
			communication_medium="Email",
			sent_or_received="Sent",
			send_email=False,
			email_template=email_template.name,
		)

		frappe.sendmail(
			recipients=recipient_list,
			subject=subject,
			content=content,
			sender=sender,
			communication=comm["name"],
			queue_separately=True,
			reference_doctype="Email Campaign",
			reference_name=campaign_name,
			unsubscribe_message=_("Unsubscribe from this campaign"),
		)
	except Exception:
		frappe.db.rollback(save_point="email_campaign_send")
		frappe.log_error(title="Email Campaign Failed.")

	return comm


# called from hooks on doc_event Email Unsubscribe
def unsubscribe_recipient(unsubscribe, method):
	if unsubscribe.reference_doctype != "Email Campaign":
		return

	email_campaign = frappe.get_doc("Email Campaign", unsubscribe.reference_name)

	if email_campaign.email_campaign_for == "Email Group":
		if unsubscribe.email:
			frappe.db.set_value(
				"Email Group Member",
				{"email_group": email_campaign.recipient, "email": unsubscribe.email},
				"unsubscribed",
				1,
			)
	else:
		# For Lead or Contact
		frappe.db.set_value("Email Campaign", email_campaign.name, "status", "Unsubscribed")


# called through hooks to update email campaign status daily
def set_email_campaign_status():
	email_campaigns = frappe.get_all(
		"Email Campaign",
		filters={"status": ("!=", "Unsubscribed")},
		pluck="name",
	)

	for name in email_campaigns:
		email_campaign = frappe.get_doc("Email Campaign", name)
		email_campaign.refresh_end_date()
		email_campaign.update_status()
