# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class GratuityRule(Document):

	def validate(self):
		for current_slab in self.gratuity_rule_slabs:
			if current_slab.from_year > current_slab.to_year:
				frappe(_("Row {0}: From (Year) can not be greater than To (Year)").format(slab.idx))

			if current_slab.to_year == 0 and current_slab.from_year == 0 and len(self.gratuity_rule_slabs) > 1:
				frappe.throw(_("You can not define multiple slabs if you have a slab with no lower and upper limits."))


