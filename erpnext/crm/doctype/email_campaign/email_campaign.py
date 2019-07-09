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
		self.set_end_date()
		self.update_status()

	def validate_dates(self):
		campaign = frappe.get_doc("Campaign", self.campaign_name)

		#email campaign cannot start before campaign
		if campaign.from_date and getdate(self.start_date) < getdate(campaign.from_date):
			frappe.throw(_("Email Campaign Start Date cannot be before Campaign Start Date"))

		#check if email_schedule is exceeding the campaign end date
		no_of_days = 0
		for entry in self.get("email_schedule"):
			no_of_days += entry.send_after_days
		email_schedule_end_date = add_days(getdate(self.start_date), no_of_days)
		if campaign.to_date and getdate(email_schedule_end_date) > getdate(campaign.to_date):
			frappe.throw(_("Email Schedule cannot extend Campaign End Date"))

	def validate_lead(self):
		lead = frappe.get_doc("Lead", self.recipient)
		if not lead.get("email_id"):
			frappe.throw(_("Please set an email id for lead communication"))

	def set_end_date(self):
		#set the end date as start date + max(send after days) in email schedule
		send_after_days = []
		for entry in self.get("email_schedule"):
			send_after_days.append(entry.send_after_days)
		self.end_date = add_days(getdate(self.start_date), max(send_after_days))

	def update_status(self):
		start_date = getdate(self.start_date)
		end_date = getdate(self.end_date)
		today_date = getdate(today())
		if self.unsubscribed:
			self.status = "Unsubscribed"
		else:
			if start_date > today_date:
				self.status = "Scheduled"
			elif end_date >= today_date:
				self.status = "In Progress"
			elif end_date < today_date:
				self.status = "Completed"

#called through hooks to send campaign mails to leads
def send_email_to_leads():
	email_campaigns = frappe.get_all("Email Campaign", filters = { 'status': ('not in', ['Unsubscribed', 'Completed', 'Scheduled']), 'unsubscribed': 0 })
	for campaign in email_campaigns:
		email_campaign = frappe.get_doc("Email Campaign", campaign.name)
		for entry in email_campaign.get("email_schedule"):
			scheduled_date = add_days(email_campaign.get('start_date'), entry.get('send_after_days'))
			if scheduled_date == getdate(today()):
				send_mail(entry, email_campaign)

def send_mail(entry, email_campaign):
	if email_campaign.email_campaign_for == "Lead":
		lead = frappe.get_doc("Lead", email_campaign.get("recipient"))
		recipient_email = lead.email_id
	elif email_campaign.email_campaign_for == "Contact":
		recipient = frappe.get_doc("Contact", email_campaign.get("recipient"))
		recipient_email = recipient.email_id
	email_template = frappe.get_doc("Email Template", entry.get("email_template"))
	sender = frappe.get_doc("User", email_campaign.get("sender"))
	sender_email = sender.email
	# send mail and link communication to document
	comm = make(
		doctype = "Email Campaign",
		name = email_campaign.name,
		subject = email_template.get("subject"),
		content = email_template.get("response"),
		sender = sender_email,
		recipients = recipient_email,
		communication_medium = "Email",
		sent_or_received = "Sent",
		send_email = False,
		email_template = email_template.name
	)
	frappe.sendmail(
		recipients = recipient_email,
		sender = sender_email,
		subject = email_template.get("subject"),
		content = email_template.get("response"),
		reference_doctype = "Email Campaign",
		reference_name = email_campaign.name,
		unsubscribe_method = "/api/method/erpnext.crm.doctype.email_campaign.email_campaign.unsubscribe_recipient",
		unsubscribe_params = {"name": email_campaign.name, "email": recipient_email},
		unsubscribe_message = "Stop Getting Email Campaign Mails",
		communication = comm.get("name")
	)

@frappe.whitelist(allow_guest=True)
def unsubscribe_recipient(name, email):
	# unsubsribe from comments and communications
	try:
		frappe.get_doc({
			"doctype": "Email Unsubscribe",
			"email": email,
			"reference_doctype": "Email Campaign",
			"reference_name": name
		}).insert(ignore_permissions=True)

	except frappe.DuplicateEntryError:
		frappe.db.rollback()

	else:
		frappe.db.commit()
	frappe.db.set_value("Email Campaign", name, "unsubscribed", 1)
	frappe.db.set_value("Email Campaign", name, "status", "Unsubscribed")
	frappe.db.commit()
	return_unsubscribed_page(email, name)

def return_unsubscribed_page(email, name):
	frappe.respond_as_web_page(_("Unsubscribed"),
		_("{0} has left the Email Campaign {1}").format(email, name),
		indicator_color='green')

#called through hooks to update email campaign status daily
def set_email_campaign_status():
	email_campaigns = frappe.get_all("Email Campaign")
	for email_campaign in email_campaigns:
		email_campaign.update_status()
