# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RepostAccountingLedger(Document):
	def validate(self):
		pass

	def validate_period_closing_voucher(self):
		pass

	def validate_vouchers(self):
		voucher_types = set([x.voucher_type for x in self.vouchers])
		for x in voucher_types:
			vouchers = set([x.voucher_no for x in self.vouchers if x.voucher_type == x])
			filtered = set(
				[x[0] for x in frappe.db.get_all(x, filters={"name": ["in", vouchers]}, as_list=1)]
			)
			# if vouchers.difference(filtered)
