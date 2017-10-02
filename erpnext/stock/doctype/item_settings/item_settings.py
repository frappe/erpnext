# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.html_utils import clean_html

class ItemSettings(Document):
	def validate(self):
		if int(self.clean_description_html or 0) \
			and not int(self.db_get('clean_description_html') or 0):
			# changed to text
			frappe.enqueue('erpnext.stock.doctype.item_settings.item_settings.clean_all_descriptions', now=frappe.flags.in_test)


def clean_all_descriptions():
	for item in frappe.get_all('Item', ['name', 'description']):
		if item.description:
			clean_description = clean_html(item.description)
		if item.description != clean_description:
			frappe.db.set_value('Item', item.name, 'description', clean_description)

