# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class HealthcareInsuranceClaim(Document):
	def on_update_after_submit(self):
		if self.claim_status != 'Pending':
			update_claim_status_to_service(self)
		if self.claim_status == 'Invoiced':
			create_journal_entry_insurance_claim(self)

def update_claim_status_to_service(doc):
	service_name = frappe.db.exists(doc.service_doctype,
	{
		'insurance_claim': doc.name,
		'claim_status': 'Pending'
	})
	if service_name:
		frappe.db.set_value(doc.service_doctype, service_name, 'claim_status', doc.claim_status)

def create_journal_entry_insurance_claim(self):
	# create jv
	sales_invoice = frappe.get_doc('Sales Invoice', self.sales_invoice)
	insurance_company = frappe.get_doc('Healthcare Insurance Company', self.insurance_company)
	from erpnext.accounts.party import get_party_account
	journal_entry = frappe.new_doc('Journal Entry')
	journal_entry.company = sales_invoice.company
	journal_entry.posting_date =  self.billing_date
	accounts = []
	tax_amount = 0.0
	accounts.append({
			'account': get_party_account('Customer', sales_invoice.customer, sales_invoice.company),
			'credit_in_account_currency': self.coverage_amount,
			'party_type': 'Customer',
			'party': sales_invoice.customer,
			'reference_type': sales_invoice.doctype,
			'reference_name': sales_invoice.name
		})
	accounts.append({
			'account': insurance_company.insurance_company_receivable_account,
			'debit_in_account_currency': self.coverage_amount,
			'party_type': 'Customer',
			'party': insurance_company.customer,
		})
	journal_entry.set('accounts', accounts)
	journal_entry.save(ignore_permissions = True)
	journal_entry.submit()
	frappe.db.set_value('Healthcare Insurance Claim', self.name, 'service_billed_jv', journal_entry.name)
	self.reload()
