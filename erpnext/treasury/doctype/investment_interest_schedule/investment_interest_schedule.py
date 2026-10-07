# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class InvestmentInterestSchedule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_interest: DF.Currency
		amortisation_amount: DF.Currency
		estimated_interest: DF.Currency
		interest_accrual: DF.Link | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		period_from: DF.Date
		period_to: DF.Date
		status: DF.Literal["Pending", "Partially Accrued", "Accrued"]
		variance: DF.Currency
	# end: auto-generated types

	pass
