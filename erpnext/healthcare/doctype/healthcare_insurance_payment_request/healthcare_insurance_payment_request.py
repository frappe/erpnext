# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, flt
from frappe.model.document import Document

class HealthcareInsurancePaymentRequest(Document):
	def validate(self):
		self.set_total()

	def set_total(self):
		total_claim_amount = 0.0
		for claim in self.claims:
			total_claim_amount += flt(claim.claim_amount)

		self.total_claim_amount = total_claim_amount

	@frappe.whitelist()
	def set_claim_items(self):
		claims = self.get_claim_items()
		for claim in claims:
			self.append('claims', {
				'insurance_claim': claim.name,
				'patient': claim.patient,
				'healthcare_service_type': claim.healthcare_service_type,
				'service_template': claim.service_template,
				'sales_invoice': claim.sales_invoice,
				'discount': claim.discount,
				'claim_coverage': claim.coverage,
				'claim_amount': claim.coverage_amount
			})

	def get_claim_items(self):
		filters = {
			'insurance_company': self.insurance_company,
			'docstatus': 1,
			'status': 'Invoiced'
		}

		if self.posting_date_type == 'Claim Posting Date':
			filters.update({
				'claim_posting_date': ('between', [self.from_date, self.to_date]),
			})
		else:
			filters.update({
				'sales_invoice_posting_date': ('between', [self.from_date, self.to_date]),
			})

		return frappe.db.get_all('Healthcare Insurance Claim',
			filters=filters,
			fields=['name', 'patient', 'healthcare_service_type', 'service_template',
				'sales_invoice', 'discount', 'coverage', 'coverage_amount'])


@frappe.whitelist()
def create_payment_entry(doc):
	import json
	from six import string_types

	if isinstance(doc, string_types):
		doc = json.loads(doc)
		doc = frappe._dict(doc)

	insurance_company_customer = frappe.db.get_value('Healthcare Insurance Company', doc.insurance_company, 'customer')
	payment_entry = frappe.new_doc('Payment Entry')
	payment_entry.voucher_type = 'Payment Entry'
	payment_entry.company = doc.company
	payment_entry.posting_date = getdate()
	payment_entry.payment_type = "Receive"
	payment_entry.party_type = "Customer"
	payment_entry.party = insurance_company_customer
	payment_entry.paid_amount= doc.total_claim_amount
	payment_entry.setup_party_account_field()
	payment_entry.set_missing_values()

	payment_entry.update({
		'reference_no': doc.name,
		'reference_date': getdate(),
		'remarks': _('Payment Entry against Insurance Claims via Healthcare Insurance Payment Request {}').format(doc.name)
	})
	return payment_entry.as_dict()
