# Copyright (c) 2015, ESS and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class SampleCollection(Document):
	def validate(self):
		if flt(self.sample_qty) <= 0:
			frappe.throw(_("Sample Quantity cannot be negative or 0"), title=_("Invalid Quantity"))
