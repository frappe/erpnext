# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from math import isfinite

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr


class PeggedCurrencies(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from erpnext.accounts.doctype.pegged_currencies.pegged_currencies import PeggedCurrencies

		pegged_currency_item: DF.Table[PeggedCurrencies]
	# end: auto-generated types

	def validate(self):
		sources = set()
		for row in self.pegged_currency_item:
			if not (row.source_currency and row.pegged_against):
				frappe.throw(
					_("Row {0}: Currency and Pegged Against are mandatory.").format(row.idx),
					title=_("Missing Currency"),
				)

			if row.source_currency == row.pegged_against:
				frappe.throw(
					_("Row {0}: {1} cannot be pegged against itself.").format(row.idx, row.source_currency),
					title=_("Invalid Pegged Currency"),
				)

			if row.source_currency in sources:
				frappe.throw(
					_("Row {0}: {1} is pegged more than once.").format(row.idx, row.source_currency),
					title=_("Duplicate Pegged Currency"),
				)
			sources.add(row.source_currency)

			self.validate_ratio(row)

	def validate_ratio(self, row):
		# the field is text, so "3,6725" must not be read as 36725
		try:
			ratio = float(cstr(row.pegged_exchange_rate).strip())
		except ValueError:
			ratio = 0

		if not isfinite(ratio) or ratio <= 0:
			frappe.throw(
				_(
					"Row {0}: Pegged Exchange Rate must be a number more than 0, with a dot as the decimal separator, not {1}."
				).format(row.idx, frappe.bold(row.pegged_exchange_rate or "''")),
				title=_("Invalid Pegged Exchange Rate"),
			)
