# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, nowdate, cstr
from frappe.model.document import Document
from frappe.core.doctype.communication.email import make

class EmailCampaign(Document):
	def validate(self):
		self.validate_dates()
		#checking if email is set for lead. Not checking for contact as email is a mandatory field for contact.
		if self.email_campaign_for == "Lead":
			self.validate_lead()
		self.update_status()

	def validate_dates(self):
		campaign = frappe.get_doc("Campaign", self.campaign_name)

		#email campaign cannot start before campaign
		if campaign.from_date and getdate(self.start_date) < getdate(campaign.from_date):
			frappe.throw(_("Email Campaign Start Date cannot be before Campaign Start Date"))

		#set the end date as start date + max(send after days) in campaign schedule
		send_after_days = []
		for entry in campaign.get("campaign_schedules"):
			send_after_days.append(entry.send_after_days)
		end_date = add_days(getdate(self.start_date), max(send_after_days))

		if campaign.to_date and getdate(end_date) > getdate(campaign.to_date):
			frappe.throw(_("Email Schedule cannot extend Campaign End Date"))
		else:
			self.end_date = end_date

	def validate_lead(self):
		lead_email_id = frappe.db.get_value("Lead", self.recipient, 'email_id')
		if not lead_email_id:
			frappe.throw(_("Please set an email id for lead communication"))

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

#called through hooks to send campaign mails to leads
def send_email_to_leads():
	email_campaigns = frappe.get_all("Email Campaign", filters = { 'status': ('not in', ['Unsubscribed', 'Completed', 'Scheduled']) })
	for camp in email_campaigns:
		email_campaign = frappe.get_doc("Email Campaign", camp.name)
		campaign = frappe.get_cached_doc("Campaign", email_campaign.campaign_name)
		for entry in campaign.get("campaign_schedules"):
			scheduled_date = add_days(email_campaign.get('start_date'), entry.get('send_after_days'))
			if scheduled_date == getdate(today()):
				send_mail(entry, email_campaign)

def send_mail(entry, email_campaign):
	recipient = frappe.db.get_value(email_campaign.email_campaign_for, email_campaign.get("recipient"), 'email_id')

	email_template = frappe.get_doc("Email Template", entry.get("email_template"))
	sender = frappe.db.get_value("User", email_campaign.get("sender"), 'email')

	# send mail and link communication to document
	comm = make(
		doctype = "Email Campaign",
		name = email_campaign.name,
		subject = email_template.get("subject"),
		content = email_template.get("response"),
		sender = sender,
		recipients = recipient,
		communication_medium = "Email",
		sent_or_received = "Sent",
		send_email = True,
		email_template = email_template.name
	)

#called from hooks on doc_event Email Unsubscribe
def unsubscribe_recipient(unsubscribe, method):
	if unsubscribe.reference_doctype == 'Email Campaign':
		frappe.db.set_value("Email Campaign", unsubscribe.reference_name, "status", "Unsubscribed")

#called through hooks to update email campaign status daily
def set_email_campaign_status():
	email_campaigns = frappe.get_all("Email Campaign", filters = { 'status': ('!=', 'Unsubscribed')})
	for entry in email_campaigns:
		email_campaign = frappe.get_doc("Email Campaign", entry.name)
		email_campaign.update_status()
