# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Mixer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		line_no: DF.Link
		mixer_body: DF.Literal["A", "B", "C"]
		mixer_code: DF.Data
		mixer_number: DF.Data
	# end: auto-generated types
	
	def autoname(self):
		line_prefix = self.line_no.split('-')[0].split(' ')[0] if self.line_no else "L1"
		name = f"{line_prefix}-{self.mixer_body}-{self.mixer_code}"
		self.name = name
		return name
	
	def before_insert(self):
		if not self.line_no:
			frappe.throw("Line no is required")
		if not self.mixer_body:
			frappe.throw("Mixer Body is required")
		if not self.mixer_code:
			frappe.throw("Mixer Code is required")
		
