# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime, timedelta
class SupportContract(Document):
	
	def validate(self):
		if self.start_date >= self.end_date:
			frappe.throw(_("Start Date of contract can't be less greater than End Date"))

def check_email():
	for email_account in frappe.get_all("Email Account", filters={"enable_incoming": 1}):
		for comm in frappe.get_all("Communication", "name", filters=[
			{"email_account":email_account.name},
			{"creation": (">", datetime.now() - timedelta(seconds = (30 * 60)))}
		]):
			comm = frappe.get_doc("Communication", comm.name)
			print("-------------------------")
			print("Subject : " + comm.subject)
			print("Content : " + comm.content)
			print("Time : " + str(comm.creation))
			print("-------------------------")