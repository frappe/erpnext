# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PricingSchemeApplication(Document):
	"""Ledger of scheme applications, written at origination submit only.

	Lifecycle mirrors GL Entry / SLE: created on submit of the origination
	document, flagged cancelled on its cancel, negative rows for returns.
	Backs Per Period accrual, caps, and reporting. Never user-edited.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		company: DF.Link | None
		discount_amount: DF.Currency
		free_item_qty: DF.Float
		is_cancelled: DF.Check
		item_code: DF.Link | None
		party: DF.DynamicLink | None
		party_type: DF.Link | None
		posting_date: DF.Date | None
		qty: DF.Float
		scheme: DF.Link
		tier_idx: DF.Int
		voucher_detail_no: DF.Data | None
		voucher_no: DF.DynamicLink | None
		voucher_type: DF.Link | None
	# end: auto-generated types

	pass
