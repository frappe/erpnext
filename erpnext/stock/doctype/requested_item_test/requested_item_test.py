# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Requested_item_test(Document):
	def on_submit(self):
		doc = frappe.get_doc("Manufacturer_test", self.manufacturer_name)
		for item in doc.item:
			if item.item_name == self.item_name and item.required_quantity == self.requested_quantity:
				item.available_quantity = self.supply_quantity
				item.required_quantity = 0
				doc.save()
		
		doc = frappe.get_doc("Warehouse_test",self.item_name)
		for vendor in doc.vendors:
			for r_vendor in self.vendors_stock:
				if vendor.vendor_name == r_vendor.vendor_name:
					vendor.quantity -= r_vendor.supply
					doc.save()
