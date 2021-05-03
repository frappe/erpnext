# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import get_link_to_form
from frappe.model.document import Document
from erpnext.healthcare.doctype.healthcare_insurance_contract.healthcare_insurance_contract import validate_insurance_contract

class HealthcareInsuranceSubscription(Document):
	def validate(self):
		validate_insurance_contract(self.insurance_company)
		self.validate_subscription_overlap()
		self.set_title()

	def validate_subscription_overlap(self):
		insurance_subscription = frappe.db.exists('Healthcare Insurance Subscription', {
			'healthcare_insurance_coverage_plan': self.healthcare_insurance_coverage_plan,
			'docstatus': 1,
			'insurance_company': self.insurance_company,
			'patient': self.patient,
			'subscription_expiry':['<=', self.subscription_expiry]
		})
		if insurance_subscription:
			frappe.throw(_('Patient {0} already has an active insurance subscription {1} with the coverage plan {2} for this period').format(
				frappe.bold(self.patient), get_link_to_form('Healthcare Insurance Subscription', insurance_subscription),
				frappe.bold(self.coverage_plan_name)), title=_('Duplicate'))

	def set_title(self):
		self.title = _('{0} with {1}').format(self.patient_name or self.patient, self.insurance_company_name or self.insurance_company)