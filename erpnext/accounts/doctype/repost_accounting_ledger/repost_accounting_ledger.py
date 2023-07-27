# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import comma_and


class RepostAccountingLedger(Document):
	def __init__(self, *args, **kwargs):
		super(RepostAccountingLedger, self).__init__(*args, **kwargs)
		self._allowed_types = set(
			["Purchase Invoice", "Sales Invoice", "Payment Entry", "Journal Entry"]
		)

	def validate(self):
		self.validate_vouchers()
		self.validate_for_closed_fiscal_year()

	def validate_for_closed_fiscal_year(self):
		if self.vouchers:
			latest_pcv = (
				frappe.db.get_all(
					"Period Closing Voucher",
					filters={"company": self.company},
					order_by="posting_date desc",
					pluck="posting_date",
					limit=1,
				)
				or None
			)
			if not latest_pcv:
				return

			for vtype in self._allowed_types:
				if names := [x.voucher_no for x in self.vouchers if x.voucher_type == vtype]:
					latest_voucher = frappe.db.get_all(
						vtype,
						filters={"name": ["in", names]},
						pluck="posting_date",
						order_by="posting_date desc",
						limit=1,
					)[0]
					if latest_voucher and latest_pcv > latest_voucher:
						frappe.throw(_("Cannot Resubmit Ledger entries for vouchers in Closed fiscal year."))

	def validate_vouchers(self):
		if self.vouchers:
			# Validate voucher types
			voucher_types = set([x.voucher_type for x in self.vouchers])
			if disallowed_types := voucher_types.difference(self._allowed_types):
				frappe.throw(
					_("{0} types are not allowed. Only {1} are.").format(
						frappe.bold(comma_and(list(disallowed_types))),
						frappe.bold(comma_and(list(self._allowed_types))),
					)
				)
