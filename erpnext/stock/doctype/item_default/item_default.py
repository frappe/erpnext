# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class ItemDefault(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		buying_cost_center: DF.Link | None
		company: DF.Link
		default_discount_account: DF.Link | None
		default_price_list: DF.Link | None
		default_provisional_account: DF.Link | None
		default_supplier: DF.Link | None
		default_warehouse: DF.Link | None
		deferred_expense_account: DF.Link | None
		deferred_revenue_account: DF.Link | None
		expense_account: DF.Link | None
		income_account: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		selling_cost_center: DF.Link | None
	# end: auto-generated types

	pass
