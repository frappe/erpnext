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
			frappe.throw(_("Not allow to set alternative item for an item {0}").format(self.item_code))

	def validate_alternative_item(self):
		if self.item_code == self.alternative_item:
			frappe.throw(_("Alternative item must not be same as item code"))

	def validate_duplicate(self):
		if frappe.db.get_value("Item Alternative", {'item_code': self.item_code,
			'alternative_item': self.alternative_item, 'name': ('!=', self.name)}):
			frappe.throw(_("Already record exists for the item {0}".format(self.item_code)))
