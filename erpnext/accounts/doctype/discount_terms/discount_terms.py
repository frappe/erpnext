# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe # pragma: no cover
from frappe.model.document import Document # pragma: no cover


class DiscountTerms(Document): # pragma: no cover
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:  # pragma: no cover
		from frappe.types import DF

		discount: DF.Float
		discount_date: DF.Date | None
		no_of_days: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
	# end: auto-generated types
	pass
