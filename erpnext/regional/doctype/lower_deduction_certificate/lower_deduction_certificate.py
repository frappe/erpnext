# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document
from erpnext.accounts.utils import get_fiscal_year

class LowerDeductionCertificate(Document):
	def validate(self):
		if getdate(self.valid_upto) < getdate(self.valid_from):
			frappe.throw(_("Valid Upto date cannot be before Valid From date"))

		fiscal_year = get_fiscal_year(fiscal_year=self.fiscal_year, as_dict=True)

		if not (fiscal_year.year_start_date <= getdate(self.valid_from) \
			<= fiscal_year.year_end_date):
			frappe.throw(_("Valid From date not in Fiscal Year {0}").format(frappe.bold(self.fiscal_year)))

		if not (fiscal_year.year_start_date <= getdate(self.valid_upto) \
			<= fiscal_year.year_end_date):
			frappe.throw(_("Valid Upto date not in Fiscal Year {0}").format(frappe.bold(self.fiscal_year)))

