# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(self,filters=None):
	columns = [
		_("Item Code") + "::140", _("Item Description") + "::240", _("Price List") + "::160", 
		_("Price List Rate") + ":Currency:120", _("criterion") + "::60"
	]	

	data = []
	RequestMaterial = frappe.get_all("Material Request Item", "item_code", filters = {"parent": self.naming_series})

	for item in RequestMaterial:
		ItemPrice = frappe.get_all("Item Price", ["item_code", "item_description", "price_list", "price_list_rate"], filters = {"item_code": item.item_code})		

		for price in ItemPrice:
			row = [price.item_code, price.item_description, price.price_list, price.price_list_rate]
			data.append(row)

	return columns, data