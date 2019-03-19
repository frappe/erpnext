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
				frappe.throw(_("A Default Service Level Agreement already exists."))

	def validate(self):
		if not self.default_service_level_agreement:
			if not (self.start_date and self.end_date):
				frappe.throw(_("Enter Start and End Date for the Agreement."))
			if self.start_date >= self.end_date:
				frappe.throw(_("Start Date of Agreement can't be greater than or equal to End Date."))

def check_agreement_status():
	service_level_agreements = frappe.get_list("Service Level Agreement", filters=[
		{"agreement_status": "Active"},
		{"default_service_level_agreement": 0}
	])
	service_level_agreements.reverse()
	for service_level_agreement in service_level_agreements:
		service_level_agreement = frappe.get_doc("Service Level Agreement", service_level_agreement)
		if service_level_agreement.end_date < frappe.utils.getdate():
			service_level_agreement.agreement_status = "Expired"
		service_level_agreement.save()

def get_active_service_level_agreement_for(customer):
	agreement = frappe.get_list("Service Level Agreement",
		filters=[{"agreement_status": "Active"}],
		or_filters=[{'customer': customer},{"default_service_level_agreement": "1"}],
		fields=["name", "service_level", "holiday_list", "priority"],
		order_by='customer DESC',
		limit=1)

	return agreement[0] if agreement else None