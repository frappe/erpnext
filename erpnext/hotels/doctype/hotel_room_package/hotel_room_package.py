# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe.model.document import Document


class HotelRoomPackage(Document):
	def validate(self):
		if not self.item:
			item = frappe.get_doc(dict(
				doctype = 'Item',
				item_code = self.name,
				item_group = 'Products',
				is_stock_item = 0,
				stock_uom = 'Unit'
			))
			item.insert()
			self.item = item.name
