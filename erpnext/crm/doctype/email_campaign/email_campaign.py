# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


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
		# checking if email is set for lead. Not checking for contact as email is a mandatory field for contact.
		if self.email_campaign_for == "Lead":
			self.validate_lead()
		self.validate_email_campaign_already_exists()
		self.update_status()

	def set_date(self):
		if getdate(self.start_date) < getdate(today()):
			frappe.throw(_("Start Date cannot be before the current date"))

		# set the end date as start date + max(send after days) in campaign schedule
		campaign = frappe.get_cached_doc("Campaign", self.campaign_name)
		send_after_days = [entry.send_after_days for entry in campaign.get("campaign_schedules")]

		if not send_after_days:
			frappe.throw(
				_("Please set up the Campaign Schedule in the Campaign {0}").format(self.campaign_name)
			)

		self.end_date = add_days(getdate(self.start_date), max(send_after_days))

	def validate_lead(self):
		lead_email_id = frappe.db.get_value("Lead", self.recipient, "email_id")
		if not lead_email_id:
			lead_name = frappe.db.get_value("Lead", self.recipient, "lead_name")
			frappe.throw(_("Please set an email id for the Lead {0}").format(lead_name))

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

	# Get all active email campaigns in a single query
	email_campaigns = frappe.get_all(
		"Email Campaign",
		filters={"status": "In Progress"},
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
				if scheduled_date == today_date:
					send_mail(entry, email_campaign)
			except Exception:
				frappe.log_error(
					title=_("Email Campaign Send Error"),
					message=_("Failed to send email for campaign {0} to {1}").format(
						email_campaign.name, email_campaign.recipient
					),
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
		email_id = frappe.db.get_value(campaign_for, recipient, "email_id")
		if not email_id:
			frappe.log_error(
				title=_("Email Campaign Error"),
				message=_("No email found for {0} {1}").format(campaign_for, recipient),
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

	# Build context for template rendering
	if campaign_for != "Email Group":
		context = {"doc": frappe.get_doc(campaign_for, recipient)}
	else:
		# For email groups, use the email group document as context
		context = {"doc": frappe.get_doc("Email Group", recipient)}

	# Render template
	subject = frappe.render_template(email_template.get("subject"), context)
	content = frappe.render_template(email_template.response_, context)

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
		)
	except Exception:
		frappe.log_error(title="Email Campaign Failed.")

	return comm


# called from hooks on doc_event Email Unsubscribe
def unsubscribe_recipient(unsubscribe, method):
	if unsubscribe.reference_doctype == "Email Campaign":
		frappe.db.set_value("Email Campaign", unsubscribe.reference_name, "status", "Unsubscribed")


# called through hooks to update email campaign status daily
def set_email_campaign_status():
	email_campaigns = frappe.get_all(
		"Email Campaign",
		filters={"status": ("!=", "Unsubscribed")},
		pluck="name",
	)

	for name in email_campaigns:
		email_campaign = frappe.get_doc("Email Campaign", name)
		email_campaign.update_status()
