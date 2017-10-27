# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class POSSettings(Document):
	def validate(self):
		self.set_link_for_pos()

	def set_link_for_pos(self):
		link = 'pos' if self.use_pos_in_offline_mode else 'point-of-sale'
		desktop_icon = frappe.db.get_value('Desktop Icon',
			{'standard': 1, 'module_name': 'POS'}, 'name')

		if desktop_icon:
			frappe.db.set_value('Desktop Icon', desktop_icon, 'link', link)