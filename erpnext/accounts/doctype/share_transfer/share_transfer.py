# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class ShareTransfer(Document):
	def validate(self):
		if self.transfer_type == 'Purchase':
			self.to_shareholder = ''
		elif (self.transfer_type == 'Issue'):
			self.from_shareholder = ''
		if self.from_shareholder == self.to_shareholder:
			frappe.throw('The seller and the buyer cannot be the same')
		if self.amount is None:
			self.amount = self.rate * self.no_of_shares
		if self.amount != self.rate * self.no_of_shares:
			frappe.throw("There's inconsistency between the rate, no of shares and the amount calculated")
		total_no_of_shares = 0
		for index, share in enumerate(self.shares):
			if share.from_no > share.to_no:
				frappe.throw("The starting share number cannot be greater than the ending share number for line {0}".format(index+1))
			total_no_of_shares += share.to_no - share.from_no + 1 
		if total_no_of_shares != self.no_of_shares:
			frappe.throw("There's inconsistency between the total no. of shares and the share numbers")