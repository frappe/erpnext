# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document


class IncomeTaxSlab(Document):
	pass


def get_applicable_income_tax_slab(payroll_period_start_date, company):
	income_tax_slab = frappe.db.sql("""
		select name
		from `tabIncome Tax Slab`
		where docstatus = 1 and disabled = 0
			and ifnull(effective_from, '2000-01-01') <= %s and company = %s
		order by ifnull(effective_from, '2000-01-01') desc
		limit 1
	""", [payroll_period_start_date, company])

	return income_tax_slab[0][0] if income_tax_slab else None
