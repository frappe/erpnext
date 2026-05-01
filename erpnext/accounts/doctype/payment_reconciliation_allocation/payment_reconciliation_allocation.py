# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PaymentReconciliationAllocation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		allocated_amount: DF.Currency
		amount: DF.Currency
		cost_center: DF.Link | None
		currency: DF.Link | None
		debit_or_credit_note_posting_date: DF.Date | None
		difference_account: DF.Link | None
		difference_amount: DF.Currency
		exchange_rate: DF.Float
		gain_loss_posting_date: DF.Date | None
		is_advance: DF.Check
		is_cross_account: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		to_pay_account: DF.Link | None
		to_pay_party: DF.DynamicLink | None
		to_pay_party_type: DF.Link | None
		to_pay_voucher_no: DF.DynamicLink
		to_pay_voucher_row: DF.Data | None
		to_pay_voucher_type: DF.Link
		to_receive_account: DF.Link | None
		to_receive_party: DF.DynamicLink | None
		to_receive_party_type: DF.Link | None
		to_receive_voucher_no: DF.DynamicLink
		to_receive_voucher_row: DF.Data | None
		to_receive_voucher_type: DF.Link
		unreconciled_amount: DF.Currency
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
