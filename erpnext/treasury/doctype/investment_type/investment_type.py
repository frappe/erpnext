# Copyright (c) 2026, Aagnya Mistry and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class InvestmentType(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		instrument_class: DF.Literal["Deposit", "Units", "Bond"]
		investment_type: DF.Data
		is_active: DF.Check
	# end: auto-generated types

	pass
