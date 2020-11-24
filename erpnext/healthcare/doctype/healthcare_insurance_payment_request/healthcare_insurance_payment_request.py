# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, nowdate
from frappe.model.document import Document

class HealthcareInsurancePaymentRequest(Document):
	def create_payment_entry(self):
		insurance_company = frappe.get_doc('Healthcare Insurance Company', self.insurance_company)
		payment_entry = frappe.new_doc('Payment Entry')
		payment_entry.voucher_type = 'Payment Entry'
		payment_entry.company = insurance_company.company
		payment_entry.posting_date =  nowdate()
		payment_entry.payment_type="Receive"
		payment_entry.party_type="Customer"
		payment_entry.party = insurance_company.customer
		payment_entry.paid_amount=self.total_claim_amount
		payment_entry.setup_party_account_field()
		payment_entry.set_missing_values()
		return payment_entry.as_dict()

@frappe.whitelist()
def get_claim_item(insurance_company, from_date=False, to_date=False, posting_date_type = ''):
	query = """
		select
			name, patient, healthcare_service_type, service_template, sales_invoice, discount, coverage, coverage_amount
		from
			`tabHealthcare Insurance Claim`
		where
			insurance_company='{0}' and docstatus=1  and claim_status="Invoiced"
	"""
	if posting_date_type == 'Claim Posting Date':
		if from_date:
			query += """ and claim_posting_date >=%(from_date)s"""
		if to_date:
			query += """ and claim_posting_date <=%(to_date)s"""
	else:
		if from_date:
			query += """ and sales_invoice_posting_date >=%(from_date)s"""
		if to_date:
			query += """ and sales_invoice_posting_date <=%(to_date)s"""

	claim_list = frappe.db.sql(query.format(insurance_company),{
			'from_date': from_date, 'to_date':to_date
		}, as_dict=True)
	if claim_list:
		return claim_list
	return False
