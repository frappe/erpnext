# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Bank(Document):
	def autoname(self):
		# first validate if company exists
		company = frappe.db.get_value("Company", self.company, ["abbr", "name"], as_dict=True)
		if not company:
			frappe.throw(_('Company {0} does not exist').format(self.company))

		self.name = self.bank_id.strip() + '-' + company.abbr