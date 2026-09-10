# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class BlanketOrderItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_price_list_rate: DF.Currency
		base_rate: DF.Currency
		item_code: DF.Link
		item_name: DF.Data | None
		ordered_qty: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		party_item_code: DF.Data | None
		price_list_rate: DF.Currency
		qty: DF.Float
		rate: DF.Currency
		terms_and_conditions: DF.Text | None
	# end: auto-generated types

	pass
