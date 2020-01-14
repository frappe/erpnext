# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document

class ItemManufacturer(Document):
	def validate(self):
		self.validate_duplicate_entry()

	def validate_duplicate_entry(self):
		if self.is_new():
			filters = {
				'item_code': self.item_code,
				'manufacturer': self.manufacturer,
				'manufacturer_part_no': self.manufacturer_part_no
			}

			if frappe.db.exists("Item Manufacturer", filters):
				frappe.throw(_("Duplicate entry against the item code {0} and manufacturer {1}")
					.format(self.item_code, self.manufacturer))

@frappe.whitelist()
def get_item_manufacturer_part_no(item_code, manufacturer):
	return frappe.db.get_value("Item Manufacturer",
		{'item_code': item_code, 'manufacturer': manufacturer}, 'manufacturer_part_no')