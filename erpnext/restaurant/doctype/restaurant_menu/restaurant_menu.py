# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class RestaurantMenu(Document):
	def validate(self):
		for d in self.items:
			if not d.rate:
				d.rate = frappe.db.get_value('Item', d.item, 'standard_rate')

	def on_update(self):
		'''Sync Price List'''
		self.make_price_list()

	def on_trash(self):
		'''clear prices'''
		self.clear_item_price()

	def clear_item_price(self, price_list=None):
		'''clear all item prices for this menu'''
		if not price_list:
			price_list = self.get_price_list().name
		frappe.db.sql('delete from `tabItem Price` where price_list = %s', price_list)

	def make_price_list(self):
		# create price list for menu
		price_list = self.get_price_list()
		self.db_set('price_list', price_list.name)

		# delete old items
		self.clear_item_price(price_list.name)

		for d in self.items:
			frappe.get_doc(dict(
				doctype = 'Item Price',
				price_list = price_list.name,
				item_code = d.item,
				price_list_rate = d.rate
			)).insert()

	def get_price_list(self):
		'''Create price list for menu if missing'''
		price_list_name = frappe.db.get_value('Price List', dict(restaurant_menu=self.name))
		if price_list_name:
			price_list = frappe.get_doc('Price List', price_list_name)
		else:
			price_list = frappe.new_doc('Price List')
			price_list.restaurant_menu = self.name
			price_list.price_list_name = self.name

		price_list.enabled = 1
		price_list.selling = 1
		price_list.save()

		return price_list


