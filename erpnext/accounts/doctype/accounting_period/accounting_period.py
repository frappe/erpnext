# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AccountingPeriod(Document):
	def validate(self):
		self.validate_overlap()

	def autoname(self):
		company_abbr = frappe.db.get_value("Company", self.company, "abbr")
		self.name = " - ".join([self.period_name, company_abbr])
	
	def validate_overlap(self):
			existing_accounting_period = frappe.db.sql("""select name from `tabAccounting Period`
				where (
					(%(start_date)s between start_date and end_date)
					or (%(end_date)s between start_date and end_date)
					or (start_date between %(start_date)s and %(end_date)s)
					or (end_date between %(start_date)s and %(end_date)s)
				) and name!=%(name)s and company=%(company)s""",
				{
					"start_date": self.start_date,
					"end_date": self.end_date,
					"name": self.name,
					"company": self.company
				}, as_dict=True)

			if len(existing_accounting_period) > 0:
				frappe.throw("Accounting Period overlaps with {0}".format(existing_accounting_period[0].get("name")))

