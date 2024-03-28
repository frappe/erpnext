# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class LedgerHealth(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		checked_on: DF.Datetime | None
		debit_credit_mismatch: DF.Check
		general_and_payment_ledger_mismatch: DF.Check
		name: DF.Int | None
		voucher_no: DF.Data | None
		voucher_type: DF.Data | None
	# end: auto-generated types

	pass
