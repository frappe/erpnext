# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact

STANDARD_USERS = ("Guest", "Administrator")

class Member(Document):
	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_address_and_contact(self)


	def validate(self):
		if self.name not in STANDARD_USERS:
			self.validate_email_type(self.email)
			self.validate_email_type(self.name)


	def validate_email_type(self, email):
		from frappe.utils import validate_email_add
		validate_email_add(email.strip(), True)

def get_timeline_data(doctype, name):
	'''returns timeline data based on membership'''
	from six import iteritems
	from frappe.utils import get_timestamp

	out = {}

	'''membership'''
	items = dict(frappe.db.sql('''select creation, count(*)
		from `tabMembership` where member=%s
			and creation > date_sub(curdate(), interval 1 year)
			group by creation''', name))

	for date, count in items.iteritems():
		timestamp = get_timestamp(date)
		out.update({ timestamp: count })

	return out