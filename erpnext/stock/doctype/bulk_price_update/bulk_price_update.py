# -*- coding: utf-8 -*-
# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, flt
from erpnext.stock.get_item_details import get_price_list_rate_for
from erpnext.stock.report.item_prices.item_prices import _set_item_pl_rate


class BulkPriceUpdate(Document):
	def update_prices(self):
		self._validate_mandatory()
		self.validate_rows()
		self.validate_duplicate()

		effective_date = getdate(self.get('effective_date'))

		for d in self.get('items'):
			if d.get('item_code'):
				price_list = self.get_price_list(d)
				rate = flt(d.get('price_list_rate'))
				uom = frappe.get_cached_value("Item", d.get('item_code'), 'stock_uom')

				_set_item_pl_rate(effective_date, d.get('item_code'), price_list, rate, uom)

		self.get_current_rates()

		frappe.msgprint(_("Prices updated"), indicator="green")

	def validate_rows(self):
		for d in self.get('items'):
			if d.get('item_code'):
				price_list = self.get_price_list(d)
				rate = flt(d.get('price_list_rate'))

				if not price_list:
					frappe.throw(_("Row #{0}: Price List is mandatory").format(d.idx))
				if not rate:
					frappe.throw(_("Row #{0}: New Rate cannot be 0").format(d.idx))

	def validate_duplicate(self):
		visited = set()
		for d in self.get('items'):
			if d.get('item_code'):
				price_list = self.get_price_list(d)
				key = (d.get('item_code'), price_list)

				if key in visited:
					frappe.throw(_("Row #{0}: Item Code {1} and Price List {2} is duplicate")
						.format(d.idx, frappe.bold(d.item_code), frappe.bold(price_list)))

				visited.add(key)

	def get_current_rates(self, row=None, unset_missing_items=True):
		missing_item_codes = []

		for d in self.get('items'):
			if row and d.name != row:
				continue

			if unset_missing_items and d.get('item_code') and not frappe.db.exists("Item", d.get('item_code')):
				missing_item_codes.append((d.item_code, d.idx))
				d.item_name = "NOT FOUND: {0}".format(d.item_code)
				d.item_code = None

			d.current_rate = self.get_current_rate(d)

		if missing_item_codes:
			item_codes_ul = "".join(["<li>Row #{0}: {1}</li>".format(missing[1], frappe.bold(missing[0]))
				for missing in missing_item_codes])
			frappe.msgprint(_("The following Item Codes were not found:<br><ul>{0}</ul>").format(item_codes_ul),
				indicator="orange")

	def get_current_rate(self, d):
		price_list = self.get_price_list(d)
		if not d.get('item_code') or not price_list:
			return None

		uom = frappe.get_cached_value("Item", d.get('item_code'), 'stock_uom')

		price_args = frappe._dict({
			'transaction_date': getdate(self.get('effective_date')),
			'item_code': d.get('item_code'),
			'uom': uom,
			'price_list': price_list
		})

		price_list_rate = get_price_list_rate_for(price_args, d.get('item_code'))
		return price_list_rate

	def get_price_list(self, d):
		return d.get('price_list') or self.get('price_list')
