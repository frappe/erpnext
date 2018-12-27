# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ServiceLevelAgreement(Document):

	def before_insert(self):
		if self.default_service_level_agreement:
			doc = frappe.get_list("Service Level Agreement", filters=[{"default_service_level_agreement": "1"}])
			if doc:
				frappe.throw(_("There can't be two Default Service Level Agreements"))

	def validate(self):
		if not self.default_service_level_agreement:
			if self.start_date >= self.end_date:
				frappe.throw(_("Start Date of contract can't be greater than or equal to End Date"))

def check_agreement_status():
	service_level_agreements = frappe.get_list("Service Level Agreement", filters={"agreement_status": "Active"})
	service_level_agreements.reverse()
	for service_level_agreement in service_level_agreements:
		service_level_agreement = frappe.get_doc("Service Level Agreement", service_level_agreement)
		if service_level_agreement.end_date < frappe.utils.getdate():
			service_level_agreement.agreement_status = "Expired"
		service_level_agreement.save()