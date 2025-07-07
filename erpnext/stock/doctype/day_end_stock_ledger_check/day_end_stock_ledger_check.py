# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DayEndStockledgerVerification(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.stock.doctype.stock_ledger_variance.stock_ledger_variance import StockLedgerVariance

		company: DF.Link | None
		entries: DF.Table[StockLedgerVariance]
		posting_date: DF.Date | None
		status: DF.Literal["", "Queued", "Completed"]
	# end: auto-generated types

	pass


def create_audit():
	pass
