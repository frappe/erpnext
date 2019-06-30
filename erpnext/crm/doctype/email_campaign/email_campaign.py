# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, add_days
from frappe.model.document import Document

class EmailCampaign(Document):
	def validate(self):
		self.validate_dates()

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
