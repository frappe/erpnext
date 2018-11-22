# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _, utils
from datetime import datetime, timedelta
class SupportContract(Document):
	
	def validate(self):
		if self.end_date < frappe.utils.nowdate():
			self.contract_status = "Expired"
		if self.start_date >= self.end_date:
			frappe.throw(_("Start Date of contract can't be less greater than End Date"))

def check_email():
	for email_account in frappe.get_all("Email Account", filters=[{"enable_incoming": 1}]):
		for comm in frappe.get_all("Communication", "name", filters=[{"email_account":email_account.name}]):
			comm = frappe.get_doc("Communication", comm.name)
			customer = frappe.get_all("Customer", filters=[{"email_id": comm.sender}], limit=1)
			support_contract = frappe.get_all("Support Contract", filters=[{"customer": customer.name}], limit=1)
			issue_criticality = frappe.get_all("Issue Criticality", support_contract.issue_criticality)
			for keyword in issue_criticality.keyword:
				print(keyword)
			print("-------------------------")
			print("Subject : " + comm.subject)
			print("Content : " + comm.content)
			print("Time : " + str(comm.creation))
			print("-------------------------")