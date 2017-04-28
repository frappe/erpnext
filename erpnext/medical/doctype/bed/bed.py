# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import cstr

class Bed(Document):
	def autoname(self):
		self.name = "-".join(filter(None,
			[cstr(self.get(f)).strip() for f in ["bed_number","parent"]]))

