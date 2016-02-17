# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Translation(Document):
	def on_update(self):
		frappe.cache().hdel('lang_user_translations', self.language_code)
