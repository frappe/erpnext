# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AssetRepairConsumedItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		consumed_quantity: DF.Data | None
		item_code: DF.Link
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		serial_and_batch_bundle: DF.Link | None
		serial_no: DF.SmallText | None
		total_value: DF.Currency
		valuation_rate: DF.Currency
		warehouse: DF.Link
	# end: auto-generated types

	pass
