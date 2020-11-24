# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document

class HealthcareServiceInsuranceCoverage(Document):
	def validate(self):
		self.validate_service_overlap()

	def validate_service_overlap(self):
		service_insurance_coverages = frappe.db.exists('Healthcare Service Insurance Coverage',
											{
											'healthcare_insurance_coverage_plan': self.healthcare_insurance_coverage_plan,
											'is_active': 1,
											'healthcare_service_template' : self.healthcare_service_template,
											'end_date':['<=', self.end_date]
											})
		if service_insurance_coverages:
			frappe.throw(_('Service {0} activated  this coverage plan {1}').format(frappe.bold(self.healthcare_service_template),
				frappe.bold(self.healthcare_insurance_coverage_plan)), title=_('Not Allowed'))

def check_insurance_on_service(service, insurance_subscription):
	valid_date = nowdate()
	insurance_subscription = frappe.get_doc('Healthcare Insurance Subscription', insurance_subscription)
	if insurance_subscription and valid_insurance(insurance_subscription.name, insurance_subscription.insurance_company, valid_date):
		if insurance_subscription.healthcare_insurance_coverage_plan:
			healthcare_service_coverage = frappe.db.exists('Healthcare Service Insurance Coverage',
										{
											'healthcare_insurance_coverage_plan': insurance_subscription.healthcare_insurance_coverage_plan,
											'healthcare_service_template': service,
											'start_date':("<=", getdate(valid_date)),
											'end_date':(">=", getdate(valid_date))
										})
			if healthcare_service_coverage:
				return True
	return False

def get_insurance_coverage_details(healthcare_insurance_coverage_plan, service):
	coverage = 0
	discount = 0
	is_auto_approval = True
	if healthcare_insurance_coverage_plan:
		healthcare_service_coverage = frappe.db.exists('Healthcare Service Insurance Coverage',
									{
										'healthcare_insurance_coverage_plan': healthcare_insurance_coverage_plan,
										'healthcare_service_template': service
									})
		if healthcare_service_coverage:
			coverage, discount = frappe.db.get_value('Healthcare Service Insurance Coverage', healthcare_service_coverage, ['coverage', 'discount'])
			approval_mandatory_for_claim = frappe.db.get_value('Healthcare Service Insurance Coverage', healthcare_service_coverage, 'approval_mandatory_for_claim')
			if approval_mandatory_for_claim:
				manual_approval_only = frappe.db.get_value('Healthcare Service Insurance Coverage', healthcare_service_coverage, 'manual_approval_only')
				if manual_approval_only:
					is_auto_approval = False
		return coverage, discount, is_auto_approval
