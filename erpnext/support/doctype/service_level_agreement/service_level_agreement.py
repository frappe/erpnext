# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class ServiceLevelAgreement(Document):

	def validate(self):
		if self.default_service_level_agreement:
			if frappe.db.exists("Service Level Agreement", {"default_service_level_agreement": "1", "name": ["!=", self.name]}):
				frappe.throw(_("A Default Service Level Agreement already exists."))
		else:
			if not (self.start_date and self.end_date) and self.ignore_start_and_end_date:
				frappe.throw(_("Enter Start and End Date for the Agreement."))

			if self.start_date >= self.end_date and self.ignore_start_and_end_date:
				frappe.throw(_("Start Date of Agreement can't be greater than or equal to End Date."))

			if self.end_date < frappe.utils.getdate() and self.ignore_start_and_end_date:
				frappe.throw(_("End Date of Agreement can't be less than today."))

def check_agreement_status():
	service_level_agreements = frappe.get_list("Service Level Agreement", filters=[
		{"agreement_status": "Active"},
		{"default_service_level_agreement": 0}
	], fields=["name", "end_date"])

	for service_level_agreement in service_level_agreements:
		if service_level_agreement.end_date < frappe.utils.getdate():
			frappe.db.set_value("Service Level Agreement", service_level_agreement.name,
				"agreement_status", "Expired")

@frappe.whitelist()
def get_active_service_level_agreement_for(priority, customer=None, service_level_agreement=None):

	if customer and frappe.db.exists("Service Level Agreement", {"customer": customer}) and not service_level_agreement:
		or_filter = {"customer": customer}
	elif service_level_agreement:
		or_filter = {"name": service_level_agreement}
	else:
		or_filter = {"default_service_level_agreement": 1}

	agreement = frappe.get_list("Service Level Agreement", filters={"agreement_status": "Active"},
		or_filters=or_filter, fields=["name", "service_level", "customer"])

	return agreement[0] if agreement else None