# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate,nowdate
from frappe.model.document import Document

class HealthcareServiceInsuranceCoverage(Document):
	def validate(self):
		self.validate_service_overlap()

	def validate_service_overlap(self):
		filters = {'healthcare_insurance_coverage_plan': self.healthcare_insurance_coverage_plan, 'is_active': 1}
		if self.name:
			filters['name'] = ('!=', self.name)
		if self.coverage_based_on == 'Service' and self.healthcare_service_template:
			filters['healthcare_service_template'] = ('=', self.healthcare_service_template)
		elif self.coverage_based_on == 'Medical Code' and self.medical_code:
			filters['medical_code'] = ('=', self.medical_code)
		elif self.coverage_based_on == 'Item' and self.item:
			filters['item'] = ('=', self.item)
		elif self.coverage_based_on == 'Item Group' and self.item_group:
			filters['item_group'] = ('=', self.item_group)
		if self.start_date:
			filters['start_date'] = ('>=', self.start_date)
		if self.end_date:
			filters['end_date'] = ('<=', self.end_date)
		service_insurance_coverages = frappe.db.exists('Healthcare Service Insurance Coverage', filters)
		if service_insurance_coverages:
			frappe.throw(_('Service/Item activated  this coverage plan {0}').format(frappe.bold(self.healthcare_insurance_coverage_plan)), title=_('Not Allowed'))

def get_service_insurance_coverage_details(service_doctype, service, service_item, insurance_subscription):
	valid_date = nowdate()
	coverage = 0
	discount = 0
	is_auto_approval = True
	insurance_details = False
	insurance_subscription = frappe.get_doc('Healthcare Insurance Subscription', insurance_subscription)
	if insurance_subscription and valid_insurance(insurance_subscription.name, insurance_subscription.insurance_company, valid_date):
		if insurance_subscription.healthcare_insurance_coverage_plan:
			healthcare_service_coverage_list = frappe.get_list('Healthcare Service Insurance Coverage',
										filters={
											'healthcare_insurance_coverage_plan': insurance_subscription.healthcare_insurance_coverage_plan,
											'is_active': 1,
											'start_date':("<=", getdate(valid_date)),
											'end_date':(">=", getdate(valid_date))
										}, fields= ['name', 'healthcare_service_template','item', 'medical_code', 'item_group'])
			if healthcare_service_coverage_list:
				if any((healthcare_service_coverage['healthcare_service_template'] == service) for healthcare_service_coverage in healthcare_service_coverage_list):
					coverage, discount, is_auto_approval = get_insurance_coverage_details(insurance_subscription.healthcare_insurance_coverage_plan, service = service)
					insurance_details = frappe._dict({'is_auto_approval': is_auto_approval, 'discount': discount, 'coverage': coverage})
				elif any((healthcare_service_coverage['item'] == service_item) for healthcare_service_coverage in healthcare_service_coverage_list):
					coverage, discount, is_auto_approval = get_insurance_coverage_details(insurance_subscription.healthcare_insurance_coverage_plan, service_item = service_item)
					insurance_details = frappe._dict({'is_auto_approval': is_auto_approval, 'discount': discount, 'coverage': coverage})
				else:
					medical_code = frappe.db.get_value(service_doctype, service, 'medical_code')
					if medical_code:
						if any((healthcare_service_coverage['medical_code'] == medical_code) for healthcare_service_coverage in healthcare_service_coverage_list):
							coverage, discount, is_auto_approval = get_insurance_coverage_details(insurance_subscription.healthcare_insurance_coverage_plan, medical_code = medical_code)
							insurance_details = frappe._dict({'is_auto_approval': is_auto_approval, 'discount': discount, 'coverage': coverage})
					else:
						item_group = frappe.db.get_value('Item', service_item, 'item_group')
						if item_group:
							if any((healthcare_service_coverage['item_group'] == item_group) for healthcare_service_coverage in healthcare_service_coverage_list):
								coverage, discount, is_auto_approval = get_insurance_coverage_details(insurance_subscription.healthcare_insurance_coverage_plan, item_group = item_group)
								insurance_details = frappe._dict({'is_auto_approval': is_auto_approval, 'discount': discount, 'coverage': coverage})
	return insurance_details

def get_insurance_coverage_details(healthcare_insurance_coverage_plan, service = None, service_item = None, medical_code = None, item_group = None):
	coverage = 0
	discount = 0
	is_auto_approval = True
	if healthcare_insurance_coverage_plan:
		filters = {'healthcare_insurance_coverage_plan': healthcare_insurance_coverage_plan, 'is_active': 1}
		if service:
			filters['healthcare_service_template'] = ('=', service)
		elif medical_code:
			filters['medical_code'] = ('=', medical_code)
		elif service_item:
			filters['item'] = ('=', service_item)
		elif item_group:
			filters['item_group'] = ('=', item_group)
		healthcare_service_coverage = frappe.db.exists('Healthcare Service Insurance Coverage', filters)
		if healthcare_service_coverage:
			coverage, discount = frappe.db.get_value('Healthcare Service Insurance Coverage', healthcare_service_coverage, ['coverage', 'discount'])
			approval_mandatory_for_claim = frappe.db.get_value('Healthcare Service Insurance Coverage', healthcare_service_coverage, 'approval_mandatory_for_claim')
			if approval_mandatory_for_claim:
				manual_approval_only = frappe.db.get_value('Healthcare Service Insurance Coverage', healthcare_service_coverage, 'manual_approval_only')
				if manual_approval_only:
					is_auto_approval = False
		return coverage, discount, is_auto_approval

def valid_insurance(insurance_subscription, insurance_company, posting_date):
	if frappe.db.exists('Healthcare Insurance Contract',
		{
			'insurance_company': insurance_company,
			'start_date':("<=", getdate(posting_date)),
			'end_date':(">=", getdate(posting_date)),
			'is_active': 1
		}):
		if frappe.db.exists('Healthcare Insurance Subscription',
			{
				'name': insurance_subscription,
				'subscription_end_date':(">=", getdate(posting_date)),
				'is_active': 1
			}):
			return True
	return False