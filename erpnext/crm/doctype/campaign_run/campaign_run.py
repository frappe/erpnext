# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.core.doctype.communication.email import make
from frappe.model.document import Document
from frappe.utils import add_days, getdate, today


class CampaignRun(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		campaign_name: DF.Link
		campaign_run_for: DF.Literal["", "Lead", "Contact", "Email Group", "List of Contacts"]
		end_date: DF.Date | None
		recipient: DF.DynamicLink
		sender: DF.Link | None
		start_date: DF.Date
		status: DF.Literal["", "Scheduled", "In Progress", "Completed", "Unsubscribed"]
	# end: auto-generated types

	def validate(self):
		self.set_date()
		# checking if email is set for lead. Not checking for contact as email is a mandatory field for contact.
		if self.campaign_run_for == "Lead":
			self.validate_lead()
		self.validate_campaign_run_already_exists()
		self.update_status()

	def set_date(self):
		if getdate(self.start_date) < getdate(today()):
			frappe.throw(_("Start Date cannot be before the current date"))
		# set the end date as start date + max(send after days) in campaign schedule
		send_after_days = []
		campaign = frappe.get_doc("Campaign", self.campaign_name)
		for entry in campaign.get("campaign_schedules"):
			send_after_days.append(entry.send_after_days)
		try:
			self.end_date = add_days(getdate(self.start_date), max(send_after_days))
		except ValueError:
			frappe.throw(
				_("Please set up the Campaign Schedule in the Campaign {0}").format(self.campaign_name)
			)

	def validate_lead(self):
		lead_email_id = frappe.db.get_value("Lead", self.recipient, "email_id")
		if not lead_email_id:
			lead_name = frappe.db.get_value("Lead", self.recipient, "lead_name")
			frappe.throw(_("Please set an email id for the Lead {0}").format(lead_name))

	def validate_campaign_run_already_exists(self):
		campaign_run_exists = frappe.db.exists(
			"Campaign Run",
			{
				"campaign_name": self.campaign_name,
				"recipient": self.recipient,
				"status": ("in", ["In Progress", "Scheduled"]),
				"name": ("!=", self.name),
			},
		)
		if campaign_run_exists:
			frappe.throw(
				_("The Campaign '{0}' already exists for the {1} '{2}'").format(
					self.campaign_name, self.campaign_run_for, self.recipient
				)
			)

	def update_status(self):
		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)
		today_date = getdate(today())
		if start_date > today_date:
			self.status = "Scheduled"
		elif end_date >= today_date:
			self.status = "In Progress"
		elif end_date < today_date:
			self.status = "Completed"


# called through hooks to send campaign mails to leads
def send_communication_to_leads_or_contacts():
	campaign_runs = frappe.get_all(
		"Campaign Run", filters={"status": ("not in", ["Unsubscribed", "Completed", "Scheduled"])}
	)
	for camp in campaign_runs:
		campaign_run = frappe.get_doc("Campaign Run", camp.name)
		campaign = frappe.get_cached_doc("Campaign", campaign_run.campaign_name)
		for entry in campaign.get("campaign_schedules"):
			scheduled_date = add_days(campaign_run.get("start_date"), entry.get("send_after_days"))
			if scheduled_date == getdate(today()):
				if entry.schedule_for == "Email Template":
					send_email(entry, campaign_run)


def send_email(entry, campaign_run):
	recipient_list = []
	if campaign_run.campaign_run_for == "Email Group":
		for member in frappe.db.get_list(
			"Email Group Member", filters={"email_group": campaign_run.get("recipient")}, fields=["email"]
		):
			recipient_list.append(member["email"])
	if campaign_run.campaign_run_for == "List of Contacts":
		for member in frappe.db.get_list(
			"List of Contacts",
			filters={"contact_list": campaign_run.get("recipient")},
			fields=["contact.email"],
		):
			recipient_list.append(member["email"])
	else:
		recipient_list.append(
			frappe.db.get_value(campaign_run.campaign_run_for, campaign_run.get("recipient"), "email_id")
		)

	email_template = frappe.get_doc("Email Template", entry.get("template"))
	sender = frappe.db.get_value("User", campaign_run.get("sender"), "email")
	context = {"doc": frappe.get_doc(campaign_run.campaign_run_for, campaign_run.recipient)}
	# send mail and link communication to document
	comm = make(
		doctype="Campaign Run",
		name=campaign_run.name,
		subject=frappe.render_template(email_template.get("subject"), context),
		content=frappe.render_template(email_template.get("response"), context),
		sender=sender,
		recipients=recipient_list,
		communication_medium="Email",
		sent_or_received="Sent",
		send_email=True,
		email_template=email_template.name,
	)
	return comm


# called from hooks on doc_event Email Unsubscribe
def unsubscribe_recipient(unsubscribe, method):
	if unsubscribe.reference_doctype == "Campaign Run":
		frappe.db.set_value("Campaign Run", unsubscribe.reference_name, "status", "Unsubscribed")


# called through hooks to update email campaign status daily
def set_campaign_run_status():
	campaign_runs = frappe.get_all("Campaign Run", filters={"status": ("!=", "Unsubscribed")})
	for entry in campaign_runs:
		campaign_run = frappe.get_doc("Campaign Run", entry.name)
		campaign_run.update_status()
		campaign_run.save()
