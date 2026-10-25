# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class ShipmentParcelTemplate(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		height: DF.Float
		length: DF.Float
		parcel_template_name: DF.Data
		weight: DF.Float
		width: DF.Float
	# end: auto-generated types

	def validate(self):
		for fieldname in ("length", "width", "height", "weight"):
			if flt(self.get(fieldname)) <= 0:
				frappe.throw(
					_("{0} must be greater than 0").format(frappe.bold(self.meta.get_label(fieldname)))
				)
