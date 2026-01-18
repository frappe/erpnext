# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ProcessPeriodClosingVoucherDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		closing_balance: DF.JSON | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		processing_date: DF.Date | None
		report_type: DF.Literal["Profit and Loss", "Balance Sheet"]
		status: DF.Literal["Queued", "Running", "Paused", "Completed", "Cancelled"]
	# end: auto-generated types

	pass
