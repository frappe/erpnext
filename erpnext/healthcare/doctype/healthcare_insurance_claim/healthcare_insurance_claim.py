# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, flt, get_link_to_form
from frappe.model.document import Document
from erpnext.healthcare.doctype.healthcare_service_insurance_coverage.healthcare_service_insurance_coverage import get_service_insurance_coverage_details

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
		journal_entry.posting_date = self.billing_date

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


def make_insurance_claim(doc, service_doctype, service, qty, billing_item=None):
	insurance_details = get_insurance_details(doc, service_doctype, service, billing_item)

	if not insurance_details:
		return

	claim = frappe.new_doc('Healthcare Insurance Claim')
	claim.patient = doc.patient
	claim.reference_dt = doc.doctype
	claim.reference_dn = doc.name
	claim.insurance_subscription = doc.insurance_subscription
	claim.insurance_company = doc.insurance_company
	claim.healthcare_service_type = service_doctype
	claim.service_template = service
	claim.approval_status = 'Approved' if insurance_details.claim_approval_mode == 'Automatic' else 'Pending'
	claim.claim_approval_mode = insurance_details.claim_approval_mode
	claim.claim_posting_date = getdate()
	claim.quantity = qty
	claim.service_doctype = doc.doctype
	claim.service_item = billing_item
	claim.discount = insurance_details.discount
	claim.price_list_rate = insurance_details.price_list_rate
	claim.amount = flt(insurance_details.price_list_rate) * flt(qty)

	if claim.discount:
		claim.discount_amount = flt(claim.price_list_rate) * flt(claim.discount) * 0.01
		claim.amount = flt(claim.price_list_rate - claim.discount_amount) * flt(qty)

	claim.coverage = insurance_details.coverage
	claim.coverage_amount = flt(claim.amount) * 0.01 * flt(claim.coverage)
	claim.flags.ignore_permissions = True
	claim.flags.ignore_mandatory = True
	claim.submit()

	update_claim_status_in_doc(doc, claim)


def get_insurance_details(doc, service_doctype, service, billing_item=None):
	if not billing_item:
		billing_item = frappe.get_cached_value(service_doctype, service, 'item')

	insurance_details = get_service_insurance_coverage_details(service_doctype, service, billing_item, doc.insurance_subscription)

	if not insurance_details:
		frappe.msgprint(_('Insurance Coverage not found for {0}: {1}').format(
			service_doctype, frappe.bold(service)))
		return

	insurance_subscription = frappe.db.get_value('Healthcare Insurance Subscription', doc.insurance_subscription,
		['insurance_company', 'healthcare_insurance_coverage_plan'], as_dict=True)
	price_list_rate = get_insurance_price_list_rate(insurance_subscription, billing_item)

	insurance_details.update({'price_list_rate': price_list_rate})

	return insurance_details


def get_insurance_price_list_rate(insurance_subscription, billing_item):
	rate = 0.0

	if insurance_subscription.healthcare_insurance_coverage_plan:
		price_list = frappe.db.get_value('Healthcare Insurance Coverage Plan', insurance_subscription.healthcare_insurance_coverage_plan, 'price_list')
		if not price_list:
			price_list = frappe.db.get_value('Healthcare Insurance Contract', {'insurance_company': insurance_subscription.insurance_company}, 'default_price_list')
			if not price_list:
				price_list = frappe.db.get_single_value('Selling Settings', 'selling_price_list')

		if price_list:
			item_price = frappe.db.exists('Item Price', {
				'item_code': billing_item,
				'price_list': price_list
			})
			if item_price:
				rate = frappe.db.get_value('Item Price', item_price, 'price_list_rate')

	return rate


def update_claim_status_in_doc(doc, claim):
	if claim:
		doc.reload()
		doc.db_set('insurance_claim', claim.name)
		doc.db_set('approval_status', claim.approval_status)

		frappe.msgprint(_('Healthcare Insurance Claim {0} created successfully').format(
			get_link_to_form('Healthcare Insurance Claim', claim.name)),
			title=_('Success'), indicator='green')


def update_insurance_claim(insurance_claim, sales_invoice_name, posting_date, total_amount):
	frappe.db.set_value('Healthcare Insurance Claim', insurance_claim, {
		'sales_invoice': sales_invoice_name,
		'sales_invoice_posting_date': posting_date,
		'billing_date': getdate(),
		'billing_amount': total_amount,
		'status': 'Invoiced'
	})