# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class PurchaseTaxesandCharges(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_currency: DF.Link | None
		account_head: DF.Link
		add_deduct_tax: DF.Literal["Add", "Deduct"]
		base_tax_amount: DF.Currency
		base_tax_amount_after_discount_amount: DF.Currency
		base_total: DF.Currency
		category: DF.Literal["Valuation and Total", "Valuation", "Total"]
		charge_type: DF.Literal[
			"",
			"Actual",
			"On Net Total",
			"On Previous Row Amount",
			"On Previous Row Total",
			"On Item Quantity",
		]
		cost_center: DF.Link | None
		description: DF.SmallText
		included_in_paid_amount: DF.Check
		included_in_print_rate: DF.Check
		is_tax_withholding_account: DF.Check
		item_wise_tax_detail: DF.Code | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		rate: DF.Float
		row_id: DF.Data | None
		tax_amount: DF.Currency
		tax_amount_after_discount_amount: DF.Currency
		total: DF.Currency
	# end: auto-generated types

	pass
