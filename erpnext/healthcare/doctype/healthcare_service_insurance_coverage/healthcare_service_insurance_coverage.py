# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, get_link_to_form
from frappe.model.document import Document

class HealthcareServiceInsuranceCoverage(Document):
	def validate(self):
		self.validate_service_overlap()
		self.set_title()

	def validate_service_overlap(self):
		filters, or_filters = self.get_filters()

		service_insurance_coverages = frappe.get_list('Healthcare Service Insurance Coverage',
			filters=filters, or_filters=or_filters)

		if service_insurance_coverages:
			frappe.throw(_('Service or Item coverage overlapping with coverage {0} under the coverage plan {1}').format(
				get_link_to_form(self.doctype, service_insurance_coverages[0].name), frappe.bold(self.healthcare_insurance_coverage_plan)),
				title=_('Not Allowed'))

	def get_filters(self):
		filters = {
			'healthcare_insurance_coverage_plan': self.healthcare_insurance_coverage_plan,
			'is_active': 1,
			'name': ['!=', self.name]
		}
		or_filters = {
			'start_date': ['<=', self.start_date],
			'end_date': ['>=', self.end_date]
		}

		if self.coverage_based_on == 'Service':
			filters['healthcare_service_template'] = self.healthcare_service_template

		elif self.coverage_based_on == 'Medical Code':
			filters['medical_code'] = self.medical_code

		elif self.coverage_based_on == 'Item':
			filters['item'] = self.item

		elif self.coverage_based_on == 'Item Group':
			filters['item_group'] = self.item_group

		return filters, or_filters

	def set_title(self):
		if self.coverage_based_on == 'Service' and self.healthcare_service_template:
			self.title = _('{0} - {1} - {2}').format(self.coverage_based_on, self.healthcare_service, self.healthcare_service_template)

		elif self.coverage_based_on == 'Medical Code' and self.medical_code:
			self.title = _('{0} - {1}').format(self.coverage_based_on , self.medical_code)

		elif self.coverage_based_on == 'Item' and self.item:
			self.title = _('{0} - {1}').format(self.coverage_based_on , self.item)

		elif self.coverage_based_on == 'Item Group' and self.item_group:
			self.title = _('{0} - {1}').format(self.coverage_based_on , self.item_group)


def get_service_insurance_coverage_details(service_doctype, service, service_item, insurance_subscription):
	valid_date = getdate()
	coverage = discount = 0
	insurance_details = False

	insurance_subscription = frappe.db.get_value('Healthcare Insurance Subscription', insurance_subscription,
		['name', 'healthcare_insurance_coverage_plan', 'insurance_company'], as_dict=True)

	coverage_plan = insurance_subscription.healthcare_insurance_coverage_plan

	if insurance_subscription and is_valid_insurance(insurance_subscription, valid_date):
		coverage_list = get_insurance_coverage_list(coverage_plan, valid_date)

		if not coverage_list:
			return

		if any((coverage['healthcare_service_template'] == service) for coverage in coverage_list):
			coverage, discount, claim_approval_mode = get_insurance_coverage_details(coverage_plan, service=service)
			insurance_details = frappe._dict({'claim_approval_mode': claim_approval_mode, 'discount': discount, 'coverage': coverage})

		elif any((coverage['item'] == service_item) for coverage in coverage_list):
			coverage, discount, claim_approval_mode = get_insurance_coverage_details(coverage_plan, service_item=service_item)
			insurance_details = frappe._dict({'claim_approval_mode': claim_approval_mode, 'discount': discount, 'coverage': coverage})

		else:
			medical_code = frappe.db.get_value(service_doctype, service, 'medical_code')
			if medical_code:
				if any((coverage['medical_code'] == medical_code) for coverage in coverage_list):
					coverage, discount, claim_approval_mode = get_insurance_coverage_details(coverage_plan, medical_code=medical_code)
					insurance_details = frappe._dict({'claim_approval_mode': claim_approval_mode, 'discount': discount, 'coverage': coverage})
			else:
				item_group = frappe.db.get_value('Item', service_item, 'item_group')
				if item_group:
					if any((coverage['item_group'] == item_group) for coverage in coverage_list):
						coverage, discount, claim_approval_mode = get_insurance_coverage_details(coverage_plan, item_group=item_group)
						insurance_details = frappe._dict({'claim_approval_mode': claim_approval_mode, 'discount': discount, 'coverage': coverage})

	return insurance_details


def get_insurance_coverage_details(coverage_plan, service=None, service_item=None,
	medical_code=None, item_group=None):
	coverage = discount = 0
	claim_approval_mode = 'Automatic'

	filters = {'healthcare_insurance_coverage_plan': coverage_plan, 'is_active': 1}

	if service:
		filters['healthcare_service_template'] = service

	elif medical_code:
		filters['medical_code'] = medical_code

	elif service_item:
		filters['item'] = service_item

	elif item_group:
		filters['item_group'] = item_group

	healthcare_service_coverage = frappe.db.exists('Healthcare Service Insurance Coverage', filters)

	if healthcare_service_coverage:
		insurance_coverage = frappe.db.get_value('Healthcare Service Insurance Coverage', healthcare_service_coverage,
			['coverage', 'discount', 'claim_approval_mode'], as_dict=True)

		coverage = insurance_coverage.coverage
		discount = insurance_coverage.discount
		claim_approval_mode = insurance_coverage.claim_approval_mode

	return coverage, discount, claim_approval_mode


def is_valid_insurance(insurance_subscription, posting_date):
	if frappe.db.exists('Healthcare Insurance Contract', {
		'insurance_company': insurance_subscription.insurance_company,
		'start_date':('<=', getdate(posting_date)),
		'end_date':('>=', getdate(posting_date)),
		'is_active': 1
	}):
		if frappe.db.exists('Healthcare Insurance Subscription', {
			'name': insurance_subscription.name,
			'subscription_expiry':('>=', getdate(posting_date))
		}):
			return True
	return False


def get_insurance_coverage_list(coverage_plan, date):
	return frappe.get_list('Healthcare Service Insurance Coverage',
		filters={
			'healthcare_insurance_coverage_plan': coverage_plan,
			'is_active': 1,
			'start_date':('<=', getdate(date))
		}, fields= ['name', 'healthcare_service_template','item', 'medical_code', 'item_group']
	)