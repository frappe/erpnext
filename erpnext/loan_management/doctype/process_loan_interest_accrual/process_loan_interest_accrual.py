# -*- coding: utf-8 -*-
# Copyright (c) 2019, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from erpnext.loan_management.doctype.loan_interest_accrual.loan_interest_accrual import make_accrual_interest_entry_for_demand_loans

class ProcessLoanInterestAccrual(Document):
	pass


@frappe.whitelist()
def process_loan_interest(posting_date):
	make_accrual_interest_entry_for_demand_loans(posting_date, from_background_job=0)
