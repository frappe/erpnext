# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TaxCategory(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		disabled: DF.Check
		title: DF.Data
	# end: auto-generated types

	pass


def get_enabled_tax_category(tax_category: str | None) -> str | None:
	"""Return the Tax Category, or None if it is disabled"""
	if tax_category and frappe.db.get_value("Tax Category", tax_category, "disabled"):
		return None

	return tax_category
