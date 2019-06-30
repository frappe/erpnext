# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, add_days, nowdate
from frappe.model.document import Document
from frappe.email.inbox import link_communication_to_document

class EmailCampaign(Document):
	def validate(self):
		self.validate_dates()
		self.validate_lead()

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
		lead = frappe.get_doc("Lead", self.lead)
		if not lead.get("email_id"):
			frappe.throw(_("Please set email id for lead communication"))

	def send(self):
		lead = frappe.get_doc("Lead", self.get("lead"))
		email_schedule =  frappe.get_doc("Campaign Email Schedule", self.get("email_schedule"))
		email_template = frappe.get_doc("Email Template", email_schedule.name)
		frappe.sendmail(
			recipients = lead.get("email_id"),
			sender = lead.get("lead_owner"),
			subject = email_template.get("subject"),
			message = email_template.get("response"),
			reference_doctype = self.doctype,
			reference_name = self.name
		)

	def on_submit(self):
		"""Create a new communication linked to the campaign if not created"""
		if not frappe.db.sql("select subject from tabCommunication where reference_name = %s", self.name):
			doc = frappe.new_doc("Communication")
			doc.subject = "Email Campaign Communication: " + self.name
			link_communication_to_document(doc, "Email Campaign", self.name, ignore_communication_links = False)

@frappe.whitelist()
def send_email_to_leads():
	email_campaigns = frappe.get_all("Email Campaign", filters = { 'start_date': ("<=", nowdate()) })
	for campaign in email_campaigns:
		email_campaign = frappe.get_doc("Email Campaign", campaign.name)
		for entry in email_campaign.get("email_schedule"):
			scheduled_date = add_days(email_campaign.get('start_date'), entry.get('send_after_days'))
			if(scheduled_date == nowdate()):
				email_campaign.send()
# send_email_to_leads()
