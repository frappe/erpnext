# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# For license information, please see license.txt


from frappe.model.document import Document


class ShippingRuleCondition(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from_value: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		shipping_amount: DF.Currency
		to_value: DF.Float
	# end: auto-generated types

	pass
