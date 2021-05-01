# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc

class Medication(Document):
	def validate(self):
		self.enable_disable_item()

	def after_insert(self):
		create_item_from_medication(self)

	def on_update(self):
		if self.item and self.change_in_item:
			self.update_item_and_item_price()

	def enable_disable_item(self):
		if self.is_billable:
			if self.disabled:
				frappe.db.set_value('Item', self.item, 'disabled', 1)
			else:
				frappe.db.set_value('Item', self.item, 'disabled', 0)

	def update_item_and_item_price(self):
		if self.is_billable:
			item_doc = frappe.get_doc('Item', {'item_code': self.item})
			item_doc.item_name = self.medication_name
			item_doc.item_group = self.item_group
			item_doc.description = self.description
			item_doc.stock_uom = self.stock_uom
			item_doc.disabled = 0
			item_doc.save(ignore_permissions=True)

			if self.rate:
				item_price = frappe.get_doc('Item Price', {'item_code': self.item})
				item_price.item_name = self.medication_name
				item_price.price_list_rate = self.rate
				item_price.save()
		else:
			frappe.db.set_value('Item', self.item, 'disabled', 1)

		self.db_set('change_in_item', 0)

def create_item_from_medication(doc):
	if not frappe.db.exists('Item', doc.item_code):
		item = frappe.get_doc({
				'doctype': 'Item',
				'item_code': doc.item_code,
				'item_name':doc.medication_name,
				'item_group': doc.item_group,
				'description':doc.description,
				'is_sales_item': 1,
				'is_stock_item': 1,
				'disabled': 0 if doc.is_billable and not doc.disabled else 1,
				'stock_uom': doc.stock_uom or frappe.db.get_single_value('Stock Settings', 'stock_uom')
		}).insert(ignore_permissions=True, ignore_mandatory=True)
	else:
		item = frappe.get_doc('Item', doc.item_code)
		if item.stock_uom != doc.stock_uom:
			frappe.throw(_('Cannot link existing Item Code {}, UOM {} does not match with Item Stock UOM')
				.format(doc.item_code, doc.stock_uom, item.stock_uom))
		item.item_name = doc.medication_name # also update the name and description of existing item
		item.description = doc.description

	make_item_price(item.name, doc.rate)
	doc.db_set('item', doc.item_code)

def make_item_price(item, item_price):
	price_list_name = frappe.db.get_value('Price List', {'selling': 1})
	frappe.get_doc({
			'doctype': 'Item Price',
			'price_list': price_list_name,
			'item_code': item,
			'price_list_rate': item_price
	}).insert(ignore_permissions=True, ignore_mandatory=True)

@frappe.whitelist()
def change_item_code_from_medication(item_code, doc):
	doc = frappe._dict(json.loads(doc))

	if frappe.db.exists('Item', {'item_code': item_code}):
		frappe.throw(_('Item with Item Code {0} already exists').format(item_code))
	else:
		rename_doc('Item', doc.item_code, item_code, ignore_permissions=True)
		frappe.db.set_value('Medication', doc.name, 'item_code', item_code)
	return
