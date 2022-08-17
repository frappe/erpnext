# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class WorkOrderInvoice(Document):
	def validate(self):
		if self.sales_invoice != None:
			self.delete_items()
			self.add_items()

	def delete_items(self):
		items = frappe.get_all("Work Order Items", ["*"], filters = {"parent": self.name})

		for item in items:
			frappe.delete_doc("Work Order Items", item.name)
	
	def add_items(self):
		items = frappe.get_all("Sales Invoice Item", ["*"], filters = {"parent": self.sales_invoice})

		for item in items:
			it = frappe.get_doc("Item", item.item_code)
			if it.is_work_order == 1:
				row = self.append("items", {})
				row.item_code = item.item_code
				row.item_name = item.item_name
				row.qty = item.qty