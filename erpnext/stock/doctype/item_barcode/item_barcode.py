# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class ItemBarcode(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		barcode: DF.Data
		barcode_type: DF.Literal[
			"",
			"EAN",
			"UPC-A",
			"CODE-39",
			"EAN-12",
			"EAN-8",
			"GS1",
			"GTIN",
			"ISBN",
			"ISBN-10",
			"ISBN-13",
			"ISSN",
			"JAN",
			"PZN",
			"UPC",
		]
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		uom: DF.Link | None
	# end: auto-generated types

	pass
