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

	def on_submit(self):
		self.update_status()

	def on_cancel(self):
		frappe.db.set_value(self.doctype, self.name, "is_cancelled", 1)
		self.update_status()

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

	def update_status(self, status=None, update_modified=True):
		if not status:
			if self.is_cancelled:
				status = "Cancelled"
			elif self.reserved_qty == self.delivered_qty:
				status = "Delivered"
			elif self.delivered_qty and self.reserved_qty > self.delivered_qty:
				status = "Partially Delivered"
			else:
				status = "Submitted"

		frappe.db.set_value(self.doctype, self.name, "status", status, update_modified=update_modified)
