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
		invoice_number: DF.DynamicLink
		invoice_type: DF.Link
		is_advance: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference_name: DF.DynamicLink
		reference_row: DF.Data | None
		reference_type: DF.Link
		unreconciled_amount: DF.Currency
	# end: auto-generated types

	@staticmethod
	def get_list(args):
		pass
