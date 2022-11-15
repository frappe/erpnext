# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, cint
from frappe.model.document import Document


class SalesCommissionCategory(Document):
	def validate(self):
		self.validate_commission_rate()
		self.validate_late_payment_deduction()

	def validate_commission_rate(self):
		if flt(self.commission_rate) < 0:
			frappe.throw(_("Commission Rate cannot be negative"))

	def validate_late_payment_deduction(self):
		days_visited = set()
		for d in self.late_payment_deduction:
			self.round_floats_in(d)

			if d.days in days_visited:
				frappe.throw(_("Row #{0}: Later Than {1} Days is duplicate").format(d.idx, frappe.bold(d.days)))

			if d.deduction_percent < 0:
				frappe.throw(_("Row #{0}: Deduction Percentage cannot be negative").format(d.idx))
			elif d.deduction_percent > 100:
				frappe.throw(_("Row #{0}: Deduction Percentage cannot be greater than 100%").format(d.idx))

			if d.days < 0:
				frappe.throw(_("Row #{0}: Later Than Days cannot be negative").format(d.idx))

			days_visited.add(d.days)

		self.late_payment_deduction = sorted(self.late_payment_deduction, key=lambda d: cint(d.days))
		for i, d in enumerate(self.late_payment_deduction):
			d.idx = i + 1


def get_commission_rate(sales_commission_category):
	if sales_commission_category:
		doc = frappe.get_cached_doc("Sales Commission Category", sales_commission_category)
		return flt(doc.commission_rate)
	else:
		return 0
