# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubcontractReceivedDetails(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bill_no: DF.Data | None
		bill_rate: DF.Currency
		diff_rate: DF.Currency
		item_code: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		po_qty: DF.Float
		po_rate: DF.Data | None
		purchase_invoice: DF.Data | None
		purchase_order: DF.Link | None
		purchase_receipt: DF.Link | None
		received_qty: DF.Float
		subcontracting_order: DF.Link | None
		subcontracting_receipt: DF.Link | None
		uom: DF.Data | None
	# end: auto-generated types
	pass
