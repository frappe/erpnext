# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AssetRepairPurchaseInvoice(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		expense_account: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		purchase_invoice: DF.Link | None
		repair_cost: DF.Currency
	# end: auto-generated types

	pass
