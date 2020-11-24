# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import getdate, nowdate
from frappe.model.document import Document

class HealthcareInsuranceSubscription(Document):
	def validate(self):
		self.validate_insurance_company()
		self.validate_subscription_overlap()

	def validate_insurance_company(self):
		contract = frappe.db.exists('Healthcare Insurance Contract',
					{
						'insurance_company': self.insurance_company,
						'end_date':(">=", nowdate()),
						'is_active': 1,
						'docstatus': 1
					})
		if not contract:
			frappe.throw(_('There is no valid contract with this Insurance Company {0}').format(self.insurance_company))

	def validate_subscription_overlap(self):
		insurance_subscription = frappe.db.exists('Healthcare Insurance Subscription',
											{
											'healthcare_insurance_coverage_plan': self.healthcare_insurance_coverage_plan,
											'is_active': 1,
											'docstatus': 1,
											'insurance_company': self.insurance_company,
											'patient': self.patient,
											'subscription_end_date':['<=', self.subscription_end_date]
											})
		if insurance_subscription:
			frappe.throw(_('Patient {0} has already subscribed coverage plan {1} this period').format(frappe.bold(self.patient),
				frappe.bold(self.healthcare_insurance_coverage_plan)), title=_('Not Allowed'))
