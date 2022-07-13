# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.query_builder.functions import Sum
from frappe.utils import flt


class CashierClosing(Document):
	def validate(self):
		self.validate_time()

	def before_save(self):
		self.get_outstanding()
		self.make_calculations()

	def get_outstanding(self):
		sales_invoice = frappe.qb.DocType("Sales Invoice")

		values = (
			frappe.qb.from_(sales_invoice)
			.select(Sum(sales_invoice.outstanding_amount))
			.where(
				(sales_invoice.owner != self.user)
				& (sales_invoice.posting_date == self.date)
				& (sales_invoice.posting_time >= self.from_time)
				& (sales_invoice.posting_time <= self.time)
			)
		).run()

		self.outstanding_amount = flt(values[0][0] if values else 0)

	def make_calculations(self):
		total = 0.00
		for i in self.payments:
			total += flt(i.amount)

		self.net_amount = (
			total + self.outstanding_amount + flt(self.expense) - flt(self.custody) + flt(self.returns)
		)

	def validate_time(self):
		if self.from_time >= self.time:
			frappe.throw(_("From Time Should Be Less Than To Time"))
