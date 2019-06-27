# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document


class AdjustmentEntryReference(Document):

	def recalculate_amounts(self, exchange_rates):
		self.payment_exchange_rate = exchange_rates[self.currency]['exchange_rate_to_payment_currency']
		self.voucher_payment_amount = self.voucher_amount * self.payment_exchange_rate
		self.balance = self.voucher_payment_amount - self.allocated_amount
		self.allocated_base_amount = self.allocated_amount * exchange_rates[self.currency][
			'exchange_rate_to_base_currency']
		allocated_amount_in_entry_currrency = self.allocated_amount / self.payment_exchange_rate
		self.gain_loss_amount = self.allocated_base_amount - allocated_amount_in_entry_currrency * self.exchange_rate
