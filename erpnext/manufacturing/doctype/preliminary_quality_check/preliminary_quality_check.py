# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PreliminaryQualityCheck(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		d1_bend: DF.Int
		d2_bend: DF.Int
		depth: DF.Literal["", "Paper Deep", "Light Paper Deep"]
		h_bend: DF.Int
		remarks: DF.Text | None
		v_bend: DF.Int
	# end: auto-generated types
	pass
