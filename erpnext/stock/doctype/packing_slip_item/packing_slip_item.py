# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


from frappe.model.document import Document


class PackingSlipItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		batch_no: DF.Link | None
		description: DF.TextEditor | None
		dn_detail: DF.Data | None
		item_code: DF.Link
		item_name: DF.Data | None
		net_weight: DF.Float
		page_break: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		pi_detail: DF.Data | None
		qty: DF.Float
		stock_uom: DF.Link | None
		weight_uom: DF.Link | None
	# end: auto-generated types

	pass
