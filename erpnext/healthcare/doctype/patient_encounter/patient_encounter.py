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
from erpnext.healthcare.utils import make_healthcare_service_order

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
		update_encounter_medical_record(self)
		create_healthcare_service_order(self)

	def on_cancel(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Open')

		if self.inpatient_record and self.drug_prescription:
			delete_ip_medication_order(self)

	def set_title(self):
		self.title = _('{0} with {1}').format(self.patient_name or self.patient,
			self.practitioner_name or self.practitioner)[:100]

	def validate_medications(self):
		if self.drug_prescription:
			for item in self.drug_prescription:
				if not item.medication and not item.drug_code:
					frappe.throw(_('Error: <b>Drug Prescription</b> Row #{} Medication or Item Code is mandatory').format(item.idx))

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


def create_healthcare_service_order(encounter):
	if encounter.drug_prescription:
		for drug in encounter.drug_prescription:
			medication = frappe.get_doc('Medication', drug.drug_code)
			args={
				'healthcare_service_order_category': medication.get_value('healthcare_service_order_category'),
				'patient_care_type': medication.get_value('patient_care_type'),
				'order_date': encounter.get_value('encounter_date'),
				'ordered_by': encounter.get_value('practitioner'),
				'order_group': encounter.name,
				'replaces': drug.get_value('replaces'),
				'patient': encounter.get_value('patient'),
				'order_doctype': 'Medication',
				'order': medication.name,
				'order_description': medication.get_value('description'),
				'intent': drug.get_value('intent'),
				'priority': drug.get_value('priority'),
				'quantity': drug.get_quantity(),
				'sequence': drug.get_value('sequence'),
				'expected_date': drug.get_value('expected_date'),
				'as_needed': drug.get_value('as_needed'),
				'occurrence': drug.get_value('occurrence'),
				'staff_role': medication.get_value('staff_role'),
				'note': drug.get_value('note'),
				'patient_instruction': drug.get_value('patient_instruction'),
				'company':encounter.company
				}
			make_healthcare_service_order(args)
	if encounter.lab_test_prescription:
		for labtest in encounter.lab_test_prescription:
			lab_template = frappe.get_doc('Lab Test Template', labtest.lab_test_code)
			args={
				'healthcare_service_order_category': lab_template.get_value('healthcare_service_order_category'),
				'patient_care_type': lab_template.get_value('patient_care_type'),
				'order_date': encounter.get_value('encounter_date'),
				'ordered_by': encounter.get_value('practitioner'),
				'order_group': encounter.name,
				'replaces': labtest.get_value('replaces'),
				'patient': encounter.get_value('patient'),
				'order_doctype': 'Lab Test Template',
				'order': lab_template.name,
				'order_description': lab_template.get_value('lab_test_description'),
				'quantity' : 1,
				'intent': labtest.get_value('intent'),
				'priority': labtest.get_value('priority'),
				'sequence': labtest.get_value('sequence'),
				'as_needed': labtest.get_value('as_needed'),
				'staff_role': lab_template.get_value('staff_role'),
				'note': labtest.get_value('note'),
				'patient_instruction': labtest.get_value('patient_instruction'),
				'healthcare_service_unit_type':lab_template.get_value('healthcare_service_unit_type'),
				'company':encounter.company
				}
			make_healthcare_service_order(args)
	if encounter.procedure_prescription:
		for procedure in encounter.procedure_prescription:
			procedure_template = frappe.get_doc('Clinical Procedure Template', procedure.procedure)
			args={
				'healthcare_service_order_category': procedure_template.get_value('healthcare_service_order_category'),
				'patient_care_type': procedure_template.get_value('patient_care_type'),
				'order_date': encounter.get_value('encounter_date'),
				'ordered_by': encounter.get_value('practitioner'),
				'order_group': encounter.name,
				'replaces': procedure.get_value('replaces'),
				'patient': encounter.get_value('patient'),
				'order_doctype': 'Clinical Procedure Template',
				'order': procedure_template.name,
				'order_description': procedure_template.get_value('description'),
				'quantity' : 1,
				'intent': procedure.get_value('intent'),
				'priority': procedure.get_value('priority'),
				'sequence': procedure.get_value('sequence'),
				'as_needed': procedure.get_value('as_needed'),
				'body_part': procedure.get_value('body_part'),
				'staff_role': procedure_template.get_value('staff_role'),
				'note': procedure.get_value('note'),
				'patient_instruction': procedure.get_value('patient_instruction'),
				'healthcare_service_unit_type':lab_template.get_value('healthcare_service_unit_type'),
				'company':encounter.company
				}
			make_healthcare_service_order(args)
	if encounter.therapies:
		for therapy in encounter.therapies:
			therapy_type = frappe.get_doc('Therapy Type', therapy.therapy_type)
			args={
				'healthcare_service_order_category': therapy_type.get_value('healthcare_service_order_category'),
				'patient_care_type': therapy_type.get_value('patient_care_type'),
				'order_date': encounter.get_value('encounter_date'),
				'ordered_by': encounter.get_value('practitioner'),
				'order_group': encounter.name,
				'replaces': therapy.get_value('replaces'),
				'patient': encounter.get_value('patient'),
				'order_doctype': 'Therapy Type',
				'order': therapy_type.name,
				'order_description': therapy_type.get_value('description'),
				'quantity' : 1,
				'intent': therapy.get_value('intent'),
				'priority': therapy.get_value('priority'),
				'sequence': therapy.get_value('sequence'),
				'as_needed': therapy.get_value('as_needed'),
				'staff_role': therapy_type.get_value('staff_role'),
				'note': therapy.get_value('note'),
				'patient_instruction': therapy.get_value('patient_instruction'),
				'company':encounter.company
				# 'healthcare_service_unit_type':therapy_type.get_value('healthcare_service_unit_type')
				}
			make_healthcare_service_order(args)
	if encounter.radiology_procedure_prescription:
		for radiology in encounter.radiology_procedure_prescription:
			radiology_template = frappe.get_doc('Radiology Examination Template', radiology.radiology_examination_template)
			args={
				'healthcare_service_order_category': radiology_template.get_value('healthcare_service_order_category'),
				'patient_care_type': radiology_template.get_value('patient_care_type'),
				'order_date': encounter.get_value('encounter_date'),
				'ordered_by': encounter.get_value('practitioner'),
				'order_group': encounter.name,
				'replaces': radiology.get_value('replaces'),
				'patient': encounter.get_value('patient'),
				'order_doctype': 'Radiology Examination Template',
				'order': radiology_template.name,
				'order_description': radiology_template.get_value('description'),
				'quantity' : 1,
				'intent': radiology.get_value('intent'),
				'priority': radiology.get_value('priority'),
				'sequence': radiology.get_value('sequence'),
				'as_needed': radiology.get_value('as_needed'),
				'staff_role': radiology_template.get_value('staff_role'),
				'note': radiology.get_value('note'),
				'patient_instruction': radiology.get_value('patient_instruction'),
				'healthcare_service_unit_type':radiology_template.get_value('healthcare_service_unit_type'),
				'company':encounter.company
				}
			make_healthcare_service_order(args)
