# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BankStatementImportLogColumnMap(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		header_text: DF.Data
		index: DF.Int
		maps_to: DF.Literal[
			"Do not import",
			"Date",
			"Withdrawal",
			"Deposit",
			"Amount",
			"Description",
			"Reference",
			"Transaction Type",
			"Debit/Credit",
			"Balance",
			"Included Fee",
			"Excluded Fee",
			"Party Name/Account Holder",
			"Party Account No.",
			"Party IBAN",
		]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		variable: DF.Data | None
	# end: auto-generated types

	pass
