# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Shareholder(Document):
	def validate(self):
		bought_shares = frappe.get_all("Share Transfer", filters = {"to_shareholder": self.shareholder})
		sold_shares = frappe.get_all("Share Transfer", filters = {"from_shareholder": self.shareholder})
		for share_transfer in bought_shares:
			transfer = frappe.get_doc('Share Transfer', share_transfer.name)
			# add to shares child table
		for share_transfer in sold_shares:
			transfer = frappe.get_doc('Share Transfer', share_transfer.name)
			# remove from shares child table
		self.update_amount()

	def update_amount(self):
		total_amount = 0
		for ledger in self.share_ledger:
			total_amount += ledger.amount
		self.total_amount = total_amount