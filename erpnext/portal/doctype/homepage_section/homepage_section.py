# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document
from frappe.utils import cint

class HomepageSection(Document):
	@property
	def column_value(self):
		return cint(12 / cint(self.no_of_columns or 3))
