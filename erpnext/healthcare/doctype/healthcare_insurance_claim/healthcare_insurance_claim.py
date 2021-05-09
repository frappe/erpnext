# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.model.document import Document

class HealthcareInsuranceClaim(Document):
	def on_update(self):
		self.update_approval_status_in_service()

	def on_update_after_submit(self):
		self.update_approval_status_in_service()

		if self.status == 'Invoiced' and not self.ref_journal_entry:
			self.create_journal_entry()

	def before_cancel(self):
		if self.approval_status == 'Approved':
			frappe.throw(_('Cannot cancel Approved Insurance Claim'))

	def on_cancel(self):
		if self.status != 'Invoiced':
			self.update_approval_status_in_service(cancel=True)

	def update_approval_status_in_service(self, cancel=False):
		service_docname = frappe.db.exists(self.service_doctype, {'insurance_claim': self.name})

		if service_docname:
			# unlink claim from service
			if cancel:
				frappe.db.set_value(self.service_doctype, service_docname, {
					'insurance_claim': '',
					'approval_status': ''
				})
				frappe.msgprint(_('Insurance Claim unlinked from the {0} {1}').format(self.service_doctype, service_docname))
			else:
				frappe.db.set_value(self.service_doctype, service_docname, 'approval_status', self.approval_status)

	def create_journal_entry(self):
		from erpnext.accounts.party import get_party_account

		sales_invoice = frappe.db.get_value('Sales Invoice', self.sales_invoice,
			['customer', 'company'], as_dict=True)

		insurance_company = frappe.get_doc('Healthcare Insurance Company', self.insurance_company,
			fields=['insurance_company_receivable_account', 'customer'], as_dict=True)

		journal_entry = frappe.new_doc('Journal Entry')
		journal_entry.company = sales_invoice.company
		journal_entry.posting_date =  self.billing_date

		journal_entry.append('accounts', {
			'account': get_party_account('Customer', sales_invoice.customer, sales_invoice.company),
			'credit_in_account_currency': self.coverage_amount,
			'party_type': 'Customer',
			'party': sales_invoice.customer,
			'reference_type': 'DocType',
			'reference_name': self.sales_invoice
		})

		journal_entry.append('accounts', {
			'account': insurance_company.insurance_company_receivable_account,
			'debit_in_account_currency': self.coverage_amount,
			'party_type': 'Customer',
			'party': insurance_company.customer
		})

		journal_entry.flags.ignore_permissions = True
		journal_entry.flags.ignore_mandatory = True
		journal_entry.submit()

		self.db_set('ref_journal_entry', journal_entry.name)

@frappe.whitelist()
def create_insurance_coverage(doc):
	from six import string_types
	import json

	if isinstance(doc, string_types):
		doc = json.loads(doc)
		doc = frappe._dict(doc)

	coverage_plan = frappe.db.get_value('Healthcare Insurance Subscription',
		doc.insurance_subscription, 'healthcare_insurance_coverage_plan')

	coverage_service = frappe.new_doc('Healthcare Service Insurance Coverage')
	coverage_service.coverage_based_on = doc.coverage_based_on
	coverage_service.healthcare_insurance_coverage_plan = coverage_plan
	coverage_service.insurance_coverage_plan_name = frappe.db.get_value('Healthcare Insurance Coverage Plan',
		coverage_plan, 'coverage_plan_name')


	if doc.coverage_based_on == 'Service':
		coverage_service.healthcare_service = doc.healthcare_service_type
		coverage_service.healthcare_service_template = doc.service_template

	elif doc.coverage_based_on == 'Medical Code':
		coverage_service.medical_code = doc.medical_code

	elif doc.coverage_based_on == 'Item':
		coverage_service.item = doc.service_item

	coverage_service.coverage = doc.coverage
	coverage_service.discount = doc.discount
	coverage_service.start_date = doc.claim_posting_date or getdate()
	coverage_service.end_date = doc.approval_validity_end_date
	return coverage_service