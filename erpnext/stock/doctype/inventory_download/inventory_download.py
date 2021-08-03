# -*- coding: utf-8 -*-
# Copyright (c) 2021, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class InventoryDownload(Document):
	def validate(self):
		if self.docstatus == 1:
			self.apply_inventory_download()
	
	def on_cancel(self):
		self.apply_inventory_download_cancel()
	
	def apply_inventory_download(self):
		items = frappe.get_all("Inventory Download Detail", ["s_warehouse", "item_code", "qty"], filters = {"parent": self.name})

		for item in items:
			bin = frappe.get_all("Bin", ["name", "actual_qty"], filters = {"warehouse": item.s_warehouse, "item_code": item.item_code})

			if len(bin) > 0:
				if bin[0].actual_qty >= item.qty:
					doc = frappe.get_doc("Bin", bin[0].name)
					doc.actual_qty -= item.qty
					doc.save()
				else:
					frappe.throw(_("There is not enough quantity to download in stock."))
			else:
				frappe.throw(_("This product does not exist in inventory with the selected warehouse."))
	
	def apply_inventory_download_cancel(self):
		items = frappe.get_all("Inventory Download Detail", ["s_warehouse", "item_code", "qty"], filters = {"parent": self.name})

		for item in items:
			bin = frappe.get_all("Bin", ["name", "actual_qty"], filters = {"warehouse": item.s_warehouse, "item_code": item.item_code})

			if len(bin) > 0:
				doc = frappe.get_doc("Bin", bin[0].name)
				doc.actual_qty += item.qty
				doc.save()
			else:
				frappe.throw(_("This product does not exist in inventory with the selected warehouse."))