# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, getdate, add_days
from frappe import _
from frappe.model.mapper import get_mapped_doc

class PatientEncounter(Document):
	def validate(self):
		self.set_title()
		self.validate_medications()

	def on_update(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Closed')

	def on_submit(self):
		if self.therapies:
			create_therapy_plan(self)

		self.make_healthcare_service_order()

	def on_cancel(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Open')

		if self.inpatient_record and self.drug_prescription:
			delete_ip_medication_order(self)

	def set_title(self):
		self.title = _('{0} with {1}').format(self.patient_name or self.patient,
			self.practitioner_name or self.practitioner)[:100]

	def validate_medications(self):
		if not self.drug_prescription:
			return

		for item in self.drug_prescription:
			if not item.medication and not item.drug_code:
				frappe.throw(_('Row #{0} (Drug Prescription): Medication or Item Code is mandatory').format(item.idx))

	def make_healthcare_service_order(self):
		if self.drug_prescription:
			for drug in self.drug_prescription:
				medication = frappe.get_doc('Medication', drug.drug_code)
				order = self.get_order_details(medication, drug)
				order.insert(ignore_permissions=True, ignore_mandatory=True)

		if self.lab_test_prescription:
			for lab_test in self.lab_test_prescription:
				lab_template = frappe.get_doc('Lab Test Template', lab_test.lab_test_code)
				order = self.get_order_details(lab_template, lab_test)
				order.insert(ignore_permissions=True, ignore_mandatory=True)

		if self.procedure_prescription:
			for procedure in self.procedure_prescription:
				procedure_template = frappe.get_doc('Clinical Procedure Template', procedure.procedure)
				order = self.get_order_details(procedure_template, procedure)
				order.insert(ignore_permissions=True, ignore_mandatory=True)

		if self.therapies:
			for therapy in self.therapies:
				therapy_type = frappe.get_doc('Therapy Type', therapy.therapy_type)
				order = self.get_order_details(therapy_type, therapy)
				order.insert(ignore_permissions=True, ignore_mandatory=True)

	def get_order_details(self, doc, line_item):
		order = frappe.get_doc({
			'doctype': 'Healthcare Service Order',
			'order_doctype': doc.doctype,
			'order_template': doc.name,
			'order_date': self.encounter_date,
			'order_time': self.encounter_time,
			'company': self.company,
			'status': 'Draft',
			'patient': self.get('patient'),
			'practitioner': self.practitioner,
			'order_group': self.name,
			'sequence': line_item.get('sequence'),
			'healthcare_service_order_category': doc.get('healthcare_service_order_category'),
			'patient_care_type': doc.get('patient_care_type'),
			'intent': line_item.get('intent'),
			'priority': line_item.get('priority'),
			'quantity': line_item.get_quantity() if line_item.doctype == 'Drug Prescription' else 1,
			'dosage': line_item.get('dosage'),
			'dosage_form': line_item.get('dosage_form'),
			'period': line_item.get('period'),
			'expected_date': line_item.get('expected_date'),
			'as_needed': line_item.get('as_needed'),
			'staff_role': doc.get('staff_role'),
			'note': line_item.get('note'),
			'patient_instruction': line_item.get('patient_instruction')
		})

		if doc.doctype == 'Lab Test Template':
			description = doc.get('lab_test_description')
		else:
			description = doc.get('description')

		order.update({'order_description': description})
		return order

@frappe.whitelist()
def make_ip_medication_order(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.start_date = source.encounter_date
		for entry in source.drug_prescription:
			if entry.drug_code:
				dosage = frappe.get_doc('Prescription Dosage', entry.dosage)
				dates = get_prescription_dates(entry.period, target.start_date)
				for date in dates:
					for dose in dosage.dosage_strength:
						order = target.append('medication_orders')
						order.drug = entry.drug_code
						order.drug_name = entry.drug_name
						order.dosage = dose.strength
						order.instructions = entry.comment
						order.dosage_form = entry.dosage_form
						order.date = date
						order.time = dose.strength_time
				target.end_date = dates[-1]

	doc = get_mapped_doc('Patient Encounter', source_name, {
			'Patient Encounter': {
				'doctype': 'Inpatient Medication Order',
				'field_map': {
					'name': 'patient_encounter',
					'patient': 'patient',
					'patient_name': 'patient_name',
					'patient_age': 'patient_age',
					'inpatient_record': 'inpatient_record',
					'practitioner': 'practitioner',
					'start_date': 'encounter_date'
				},
			}
		}, target_doc, set_missing_values)

	return doc


def get_prescription_dates(period, start_date):
	prescription_duration = frappe.get_doc('Prescription Duration', period)
	days = prescription_duration.get_days()
	dates = [start_date]
	for i in range(1, days):
		dates.append(add_days(getdate(start_date), i))
	return dates


def create_therapy_plan(encounter):
	if len(encounter.therapies):
		doc = frappe.new_doc('Therapy Plan')
		doc.patient = encounter.patient
		doc.start_date = encounter.encounter_date
		for entry in encounter.therapies:
			doc.append('therapy_plan_details', {
				'therapy_type': entry.therapy_type,
				'no_of_sessions': entry.no_of_sessions
			})
		doc.save(ignore_permissions=True)
		if doc.get('name'):
			encounter.db_set('therapy_plan', doc.name)
			frappe.msgprint(_('Therapy Plan {0} created successfully.').format(frappe.bold(doc.name)), alert=True)


def delete_ip_medication_order(encounter):
	record = frappe.db.exists('Inpatient Medication Order', {'patient_encounter': encounter.name})
	if record:
		frappe.delete_doc('Inpatient Medication Order', record, force=1)
