# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Shareholder(Document):
	def validate(self):
		self.update_amount()

	def update_amount(self):
		total_amount = 0
		for ledger in self.share_ledger:
			ledger.amount = ledger.rate * ledger.no_of_shares
			total_amount += ledger.amount
		self.total_amount = total_amount