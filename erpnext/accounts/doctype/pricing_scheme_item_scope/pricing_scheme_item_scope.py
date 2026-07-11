# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PricingSchemeItemScope(Document):
	"""Scope row shared by trigger scope and benefit scope tables.

	Matching semantics live in erpnext.accounts.services.pricing.pricing_matching:
	OR within a scope type, AND across scope types, excludes subtract.
	"""

	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		exclude: DF.Check
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		scope_type: DF.Literal["Item Group", "Item", "Brand", "All Items"]
		uom: DF.Link | None
		value: DF.DynamicLink | None
	# end: auto-generated types

	pass
