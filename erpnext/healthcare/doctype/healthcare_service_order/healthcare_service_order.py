# -*- coding: utf-8 -*-
# Copyright (c) 2020, earthians and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import dateutil
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate

class HealthcareServiceOrder(Document):
	def validate(self):
		self.set_patient_details()
		self.set_order_details()
		self.set_title()

	def set_title(self):
		if frappe.flags.in_import and self.title:
			return

		self.title = f'{self.patient_name} - {self.order_template}'

	def before_submit(self):
		if self.status != 'Active':
			self.status = 'Active'

	def set_patient_details(self):
		if self.patient:
			patient = frappe.get_doc('Patient', self.patient)
			self.gender = patient.sex
			self.patient_age_data = patient.get_age()
			self.patient_birth_date = patient.dob
			self.patient_age = dateutil.relativedelta.relativedelta(getdate(), getdate(patient.dob))
			self.patient_blood_group = patient.blood_group
			self.patient_email = patient.email
			self.patient_mobile = patient.mobile
			self.inpatient_record = patient.inpatient_record
			self.inpatient_status = patient.inpatient_status
		else:
			frappe.throw(_('Patient is mandatory to create Healthcare Service Order'))

	def set_order_details(self):
		if self.order_doctype and self.order_template:
			order_template = frappe.get_doc(self.order_doctype, self.order_template)
			if not self.healthcare_service_order_category and order_template.get('healthcare_service_order_category'):
				self.healthcare_service_order_category = order_template.healthcare_service_order_category
			if not self.patient_care_type and order_template.get('patient_care_type'):
				self.patient_care_type = order_template.patient_care_type
			if not self.staff_role and order_template.get('staff_role'):
				self.staff_role = order_template.staff_role
		else:
			frappe.throw(_('Order Type and Order Template are mandatory to create Healthcare Service Order'))


@frappe.whitelist()
def set_status(docname, status):
	frappe.db.set_value('Healthcare Service Order', docname, 'status', status)