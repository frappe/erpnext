# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ItemAttribute(Document):
	def validate(self):
		values, abbrs = [], []
		for d in self.item_attribute_values:
			if d.attribute_value in values:
				frappe.throw(_("{0} must appear only once").format(d.attribute_value))
			values.append(d.attribute_value)

			if d.abbr in abbrs:
				frappe.throw(_("{0} must appear only once").format(d.abbr))
			abbrs.append(d.abbr)
