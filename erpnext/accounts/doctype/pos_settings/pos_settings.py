# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class POSSettings(Document):
	def validate(self):
		link = 'point-of-sale' if self.type_of_pos == 'Online' else 'pos'
		desktop_icon = frappe.db.get_value('Desktop Icon', {'module_name': 'POS'}, 'name')
		if desktop_icon:
			doc = frappe.get_doc('Desktop Icon', desktop_icon)
			doc.link = link
			doc.save()