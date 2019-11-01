# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from erpnext.accounts.deferred_revenue import convert_deferred_expense_to_expense, \
	convert_deferred_revenue_to_income

class ProcessDeferredAccounting(Document):
	def validate(self):
		self.validate_reference_doc()

	def on_submit(self):
		if self.type == 'Income':
			convert_deferred_revenue_to_income(self.start_date, self.end_date)
		else:
			convert_deferred_expense_to_expense(self.start_date, self.end_date)

def create_deferred_accounting_record(record_type, document_type, start_date, end_date):
	''' Create deferred accounting entry '''
	doc = frappe.get_doc(dict(
		doctype='Process Deferred Accounting',
		start_date=start_date,
		end_date=end_date,
		document_type=document_type,
		record_type=record_type
	))

	doc.insert()
	doc.submit()