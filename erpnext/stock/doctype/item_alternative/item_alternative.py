# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class ItemAlternative(Document):
	def validate(self):
		self.has_alternative_item()
		self.validate_alternative_item()
		self.validate_duplicate()

	def has_alternative_item(self):
		if (self.item_code and
			not frappe.db.get_value('Item', self.item_code, 'allow_alternative_item')):
			frappe.throw(_("Not allow to set alternative item for the item {0}").format(self.item_code))

	def validate_alternative_item(self):
		if self.item_code == self.alternative_item_code:
			frappe.throw(_("Alternative item must not be same as item code"))

		item_meta = frappe.get_meta("Item")
		fields = ["is_stock_item", "include_item_in_manufacturing","has_serial_no","has_batch_no"]
		item_data = frappe.db.get_values("Item", self.item_code, fields, as_dict=1)
		alternative_item_data = frappe.db.get_values("Item", self.alternative_item_code, fields, as_dict=1)

		for field in fields:
			if  item_data[0].get(field) != alternative_item_data[0].get(field):
				raise_exception, alert = [1, False] if field == "is_stock_item" else [0, True]

				frappe.msgprint(_("The value of {0} differs between Items {1} and {2}") \
					.format(frappe.bold(item_meta.get_label(field)),
							frappe.bold(self.alternative_item_code),
							frappe.bold(self.item_code)),
					alert=alert, raise_exception=raise_exception)

	def validate_duplicate(self):
		if frappe.db.get_value("Item Alternative", {'item_code': self.item_code,
			'alternative_item_code': self.alternative_item_code, 'name': ('!=', self.name)}):
			frappe.throw(_("Already record exists for the item {0}").format(self.item_code))

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_alternative_items(doctype, txt, searchfield, start, page_len, filters):
	return frappe.db.sql(""" (select alternative_item_code from `tabItem Alternative`
			where item_code = %(item_code)s and alternative_item_code like %(txt)s)
		union
			(select item_code from `tabItem Alternative`
			where alternative_item_code = %(item_code)s and item_code like %(txt)s
			and two_way = 1) limit {0}, {1}
		""".format(start, page_len), {
			"item_code": filters.get('item_code'),
			"txt": '%' + txt + '%'
		})
