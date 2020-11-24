# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate,nowdate
from frappe.model.document import Document

class HealthcareInsuranceClaim(Document):
	def after_insert(self):
		if self.create_coverage:
			create_coverage_for_service_or_item(self)
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
def create_coverage_for_service_or_item(self):
	healthcare_insurance_coverage_plan = frappe.db.get_value('Healthcare Insurance Subscription', self.insurance_subscription, 'healthcare_insurance_coverage_plan')
	if healthcare_insurance_coverage_plan:
		coverage_based_on = ''
		if self.healthcare_service_type and self.service_template:
			coverage_based_on = 'Service'
		elif self.medical_code:
			coverage_based_on = 'Medical Code'
		elif self.service_item:
			coverage_based_on = 'Item'
		coverage_service = frappe.new_doc('Healthcare Service Insurance Coverage')
		coverage_service.coverage_based_on = coverage_based_on
		coverage_service.healthcare_insurance_coverage_plan = healthcare_insurance_coverage_plan
		coverage_service.healthcare_service = self.healthcare_service_type if self.healthcare_service_type and coverage_based_on == 'Service' else ''
		coverage_service.healthcare_service_template = self.service_template if self.service_template and coverage_based_on == 'Service' else  ''
		coverage_service.medical_code = self.medical_code if self.medical_code and coverage_based_on == 'Medical Code' else ''
		coverage_service.item = self.service_item if self.service_item and coverage_based_on == 'Item' else  ''
		coverage_service.coverage = self.coverage if self.coverage else 0
		coverage_service.discount = self.discount if self.discount else 0
		coverage_service.start_date = self.claim_posting_date if self.claim_posting_date else nowdate()
		coverage_service.end_date = self.approval_validity_end_date if self.approval_validity_end_date else nowdate()
		coverage_service.save(ignore_permissions = True)
