# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Manufacturer_test(Document):
	def validate(self):
		for item in self.item:
			print(item.as_dict())
			if item.required_quantity:
				vendor = []
				doc = frappe.get_doc({
					'doctype': 'Requested_item_test',
					'manufacturer_name' : self.manufacturer_name,
					'item_name' : item.item_name,
					'requested_quantity' : item.required_quantity,
					})

				for name in frappe.db.get_all('Vendors_test'):
					vendor_details= frappe.get_doc('Vendors_test',{
						'name': name.name,
						'parent': item.item_name
					})
					row = {'vendor_name': vendor_details.vendor_name, 'available_quantity': vendor_details.quantity}
					doc.append('vendors_stock',row)
				doc.insert()
