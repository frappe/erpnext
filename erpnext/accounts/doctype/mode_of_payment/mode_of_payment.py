# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

from frappe.model.document import Document

class ModeofPayment(Document):
	def validate(self):
		self.validate_company_account()
		
	def validate_company_account(self):
		for d in self.accounts:
			if d.company!= frappe.db.get_value('Account', d.default_account, 'company'):
				frappe.throw("Account {0} does not belong to company {1}".format(d.default_account,d.company))