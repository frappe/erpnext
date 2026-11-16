# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


import frappe
from frappe.model.document import Document


class UOMConversionDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		conversion_factor: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		target_uom: DF.Link | None
		uom: DF.Link
	# end: auto-generated types

	@property
	def target_uom(self):
		if self.parent_doc:
			return self.parent_doc.get("stock_uom")
		if self.parent:
			return frappe.get_cached_value("Item", self.parent, "stock_uom")
