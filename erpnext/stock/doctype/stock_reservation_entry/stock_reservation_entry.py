# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from erpnext.utilities.transaction_base import TransactionBase


class StockReservationEntry(TransactionBase):
	def validate(self):
		from erpnext.stock.utils import validate_disabled_warehouse, validate_warehouse_company

		self.validate_posting_time()
		self.validate_mandatory()
		validate_disabled_warehouse(self.warehouse)
		validate_warehouse_company(self.warehouse, self.company)

	def validate_mandatory(self):
		mandatory = [
			"item_code",
			"warehouse",
			"posting_date",
			"posting_time",
			"voucher_type",
			"voucher_no",
			"voucher_detail_no",
			"reserved_qty",
			"company",
		]
		for d in mandatory:
			if not self.get(d):
				frappe.throw(_("{0} is required").format(self.meta.get_label(d)))

	def on_cancel(self):
		frappe.db.set_value(self.doctype, self.name, "is_cancelled", 1)
