# -*- coding: utf-8 -*-
# Copyright (c) 2017, sathishpy@gmail.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class BankStatementSettings(Document):
	def autoname(self):
		self.name = self.bank_account + "-Mappings"
