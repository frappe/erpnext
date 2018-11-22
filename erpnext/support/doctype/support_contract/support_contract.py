# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class SupportContract(Document):
	pass

def check_email():
	print("=======================check_email scheduled=======================")
	for email_account in frappe.get_all("Email Account"):
		print(email_account.name, email_account)
		for comm in frappe.get_all("Communication", "name", filters=[{"email_account":email_account.name}]):
			comm = frappe.get_doc("Communication", comm.name)
			print(comm.subject)