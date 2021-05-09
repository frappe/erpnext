# -*- coding: utf-8 -*-
# Copyright (c) 2020, earthians and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import dateutil
import json
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate
from six import string_types
from erpnext.healthcare.doctype.healthcare_insurance_claim.healthcare_insurance_claim import make_insurance_claim

class HealthcareServiceOrder(Document):
	def validate(self):
		self.set_patient_age()
		self.set_order_details()
		self.set_title()

	def on_submit(self):
		if self.insurance_subscription and not self.insurance_claim:
			make_insurance_claim(
				doc=self,
				service_doctype=self.order_doctype,
				service=self.order_template,
				qty=self.quantity,
				billing_item=self.billing_item
			)

	def set_title(self):
		if frappe.flags.in_import and self.title:
			return

		self.title = f'{self.patient_name} - {self.order_template}'

	def before_submit(self):
		if self.status != 'Active':
			self.status = 'Active'

	def set_patient_age(self):
		patient = frappe.get_doc('Patient', self.patient)
		self.patient_age_data = patient.get_age()
		self.patient_age = dateutil.relativedelta.relativedelta(getdate(), getdate(patient.dob))

	def set_order_details(self):
		if self.order_doctype and self.order_template:
			order_template = frappe.get_doc(self.order_doctype, self.order_template)

			if not self.patient_care_type and order_template.get('patient_care_type'):
				self.patient_care_type = order_template.patient_care_type

			if not self.staff_role and order_template.get('staff_role'):
				self.staff_role = order_template.staff_role
		else:
			frappe.throw(_('Order Type and Order Template are mandatory to create Healthcare Service Order'))


@frappe.whitelist()
def set_status(docname, status):
	frappe.db.set_value('Healthcare Service Order', docname, 'status', status)


@frappe.whitelist()
def make_clinical_procedure(service_order):
	if isinstance(service_order, string_types):
		service_order = json.loads(service_order)
		service_order = frappe._dict(service_order)

	doc = frappe.new_doc('Clinical Procedure')
	doc.procedure_template = service_order.order_template
	doc.healthcare_service_order = service_order.name
	doc.company = service_order.company
	doc.patient = service_order.patient
	doc.patient_name = service_order.patient_name
	doc.patient_sex = service_order.patient_gender
	doc.patient_age = service_order.patient_age_data
	doc.inpatient_record = service_order.inpatient_record
	doc.practitioner = service_order.practitioner
	doc.start_date = service_order.occurrence_date
	doc.start_time = service_order.occurrence_time
	doc.medical_department = service_order.medical_department
	doc.medical_code = service_order.medical_code

	return doc


@frappe.whitelist()
def make_lab_test(service_order):
	if isinstance(service_order, string_types):
		service_order = json.loads(service_order)
		service_order = frappe._dict(service_order)

	doc = frappe.new_doc('Lab Test')
	doc.template = service_order.order_template
	doc.healthcare_service_order = service_order.name
	doc.company = service_order.company
	doc.patient = service_order.patient
	doc.patient_name = service_order.patient_name
	doc.patient_sex = service_order.patient_gender
	doc.patient_age = service_order.patient_age_data
	doc.inpatient_record = service_order.inpatient_record
	doc.email = service_order.patient_email
	doc.mobile = service_order.patient_mobile
	doc.practitioner = service_order.practitioner
	doc.requesting_department = service_order.medical_department
	doc.date = service_order.occurrence_date
	doc.time = service_order.occurrence_time
	doc.invoiced = service_order.invoiced
	doc.medical_code = service_order.medical_code

	return doc

@frappe.whitelist()
def make_therapy_session(service_order):
	if isinstance(service_order, string_types):
		service_order = json.loads(service_order)
		service_order = frappe._dict(service_order)

	doc = frappe.new_doc('Therapy Session')
	doc.therapy_type = service_order.order_template
	doc.healthcare_service_order = service_order.name
	doc.company = service_order.company
	doc.patient = service_order.patient
	doc.patient_name = service_order.patient_name
	doc.gender = service_order.patient_gender
	doc.patient_age = service_order.patient_age_data
	doc.practitioner = service_order.practitioner
	doc.department = service_order.medical_department
	doc.start_date = service_order.occurrence_date
	doc.start_time = service_order.occurrence_time
	doc.invoiced = service_order.invoiced
	doc.medical_code = service_order.medical_code

	return doc