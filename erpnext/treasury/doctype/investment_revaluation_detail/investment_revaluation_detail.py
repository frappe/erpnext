# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class InvestmentRevaluationDetail(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		adjustment_amount: DF.Currency
		book_value: DF.Currency
		conversion_rate: DF.Float
		fair_value: DF.Currency
		instrument_class: DF.Data | None
		investment: DF.Link
		investment_currency: DF.Link | None
		market_price: DF.Currency
		measurement_category: DF.Data | None
		nav_per_unit: DF.Currency
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		posts_gl_entry: DF.Check
		previous_amount: DF.Currency
		units_held: DF.Float
		unrealised_gain_loss: DF.Currency
	# end: auto-generated types

	pass
