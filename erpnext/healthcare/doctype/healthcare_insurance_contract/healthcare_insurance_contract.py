# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import getdate, get_link_to_form
from frappe.model.document import Document

class HealthcareInsuranceContract(Document):
	def validate(self):
		if self.is_active:
			contract = frappe.db.exists('Healthcare Insurance Contract', {
				'insurance_company': self.insurance_company,
				'start_date':('<=', getdate()),
				'end_date':('>=', getdate()),
				'is_active': 1,
				'name': ('!=', self.name)
			})
			if contract:
				frappe.throw(_('An active contract with this insurance company already exists: {0}').format(
					get_link_to_form('Healthcare Insurance Contract', contract)), title=_('Duplicate Contract'))


def validate_insurance_contract(insurance_company):
	contract = frappe.db.exists('Healthcare Insurance Contract', {
		'insurance_company': insurance_company,
		'end_date':('>=', getdate()),
		'is_active': 1,
		'docstatus': 1
	})

	if not contract:
		frappe.throw(_('There is no valid contract with this Insurance Company {0}').format(insurance_company))