# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class LandedCostItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		applicable_charges: DF.Currency
		cost_center: DF.Link | None
		description: DF.TextEditor
		is_fixed_asset: DF.Check
		item_code: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		purchase_receipt_item: DF.Data | None
		qty: DF.Float
		rate: DF.Currency
		receipt_document: DF.DynamicLink | None
		receipt_document_type: DF.Literal["Purchase Invoice", "Purchase Receipt"]
	# end: auto-generated types

	pass
