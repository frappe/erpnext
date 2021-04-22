# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Item_test(Document):
	def validate(self):
		if(not frappe.db.exists('Warehouse_test', self.item_name)):
			doc = frappe.new_doc("Warehouse_test")
			doc.warehouse_name = self.item_name
			doc.save()
