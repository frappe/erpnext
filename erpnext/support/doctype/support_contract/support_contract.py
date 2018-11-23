# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _, utils
import re
from frappe.email.inbox import make_issue_from_communication
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
			support_contract = frappe.get_list("Support Contract", filters=[{"email_id": comm.sender}, {"contract_status": "Active"}], fields=["contract_template", "service_level", "issue_criticality", "employee_group"], limit=1)
			if support_contract:
				service_level = frappe.get_doc("Service Level", support_contract[0].service_level)
				print(service_level.support_and_resolution)
				#issue_criticality = frappe.get_doc("Issue Criticality", support_contract[0].issue_criticality)
				#for keyword in issue_criticality.keyword:
				#	if re.search(r''+ keyword.keyword +'', comm.subject) or re.search(r''+ keyword.keyword +'', comm.content):
				#		issue = make_issue_from_communication(comm.name)