# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PricingSchemePartyScope(Document):
	"""Party scope row: empty table on the scheme means all parties.

	Group and Territory values match their subtree (nested set).
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
		party_type: DF.Literal[
			"Customer",
			"Customer Group",
			"Territory",
			"Sales Partner",
			"Campaign",
			"Supplier",
			"Supplier Group",
		]
		value: DF.DynamicLink
	# end: auto-generated types

	pass
