# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt


from frappe.model.document import Document


class PaymentReconciliationEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		account_type: DF.Data | None
		amount: DF.Currency
		cost_center: DF.Link | None
		currency: DF.Link | None
		due_date: DF.Date | None
		exchange_rate: DF.Float
		is_advance: DF.Check
		is_return: DF.Check
		outstanding_amount: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		posting_date: DF.Date | None
		reference_doctype: DF.Link | None
		reference_name: DF.DynamicLink | None
		voucher_no: DF.DynamicLink | None
		voucher_row: DF.Data | None
		voucher_type: DF.Link | None
	# end: auto-generated types

	def load_from_db(self):
		pass

	def db_insert(self, *args, **kwargs):
		pass

	def db_update(self, *args, **kwargs):
		pass

	def delete(self):
		pass

	@staticmethod
	def get_list(args):
		pass

	@staticmethod
	def get_count(args):
		pass

	@staticmethod
	def get_stats(args):
		pass
