# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, getdate, add_days
from frappe import _

class PatientEncounter(Document):
	def validate(self):
		self.set_title()

	def on_update(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Closed')
		update_encounter_medical_record(self)

	def after_insert(self):
		insert_encounter_to_medical_record(self)

	def on_submit(self):
		if self.inpatient_record and self.drug_prescription:
			can_create_order = False
			for entry in self.drug_prescription:
				if entry.drug_code:
					can_create_order = True
			if can_create_order:
				create_ip_medication_order(self)

		if self.therapies:
			create_therapy_plan(self)

		update_encounter_medical_record(self)

	def on_cancel(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Open')
		delete_medical_record(self)

	def set_title(self):
		self.title = _('{0} with {1}').format(self.patient_name or self.patient,
			self.practitioner_name or self.practitioner)[:100]

def create_ip_medication_order(encounter):
	doc = frappe.new_doc('Inpatient Medication Order')
	doc.patient_encounter = encounter.name
	doc.patient = encounter.patient
	doc.patient_name = encounter.patient_name
	doc.patient_age = encounter.patient_age
	doc.inpatient_record = encounter.inpatient_record
	doc.practitioner = encounter.practitioner
	doc.start_date = encounter.encounter_date

	for entry in encounter.drug_prescription:
		if entry.drug_code:
			dosage = frappe.get_doc('Prescription Dosage', entry.dosage)
			dates = get_prescription_dates(entry.period, doc.start_date)
			for date in dates:
				for dose in dosage.dosage_strength:
					order = doc.append('medication_orders')
					order.drug = entry.drug_code
					order.drug_name = entry.drug_name
					order.dosage = dose.strength
					order.dosage_form = entry.dosage_form
					order.date = date
					order.time = dose.strength_time
	doc.save(ignore_permissions=True)

def get_prescription_dates(period, start_date):
	prescription_duration = frappe.get_doc('Prescription Duration', period)
	days = prescription_duration.get_days()
	dates = [start_date]
	for i in range(days):
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

def insert_encounter_to_medical_record(doc):
	subject = set_subject_field(doc)
	medical_record = frappe.new_doc('Patient Medical Record')
	medical_record.patient = doc.patient
	medical_record.subject = subject
	medical_record.status = 'Open'
	medical_record.communication_date = doc.encounter_date
	medical_record.reference_doctype = 'Patient Encounter'
	medical_record.reference_name = doc.name
	medical_record.reference_owner = doc.owner
	medical_record.save(ignore_permissions=True)

def update_encounter_medical_record(encounter):
	medical_record_id = frappe.db.exists('Patient Medical Record', {'reference_name': encounter.name})

	if medical_record_id and medical_record_id[0][0]:
		subject = set_subject_field(encounter)
		frappe.db.set_value('Patient Medical Record', medical_record_id[0][0], 'subject', subject)
	else:
		insert_encounter_to_medical_record(encounter)

def delete_medical_record(encounter):
	frappe.delete_doc_if_exists('Patient Medical Record', 'reference_name', encounter.name)

def set_subject_field(encounter):
	subject = frappe.bold(_('Healthcare Practitioner: ')) + encounter.practitioner + '<br>'
	if encounter.symptoms:
		subject += frappe.bold(_('Symptoms: ')) + '<br>'
		for entry in encounter.symptoms:
			subject += cstr(entry.complaint) + '<br>'
	else:
		subject += frappe.bold(_('No Symptoms')) + '<br>'

	if encounter.diagnosis:
		subject += frappe.bold(_('Diagnosis: ')) + '<br>'
		for entry in encounter.diagnosis:
			subject += cstr(entry.diagnosis) + '<br>'
	else:
		subject += frappe.bold(_('No Diagnosis')) + '<br>'

	if encounter.drug_prescription:
		subject += '<br>' + _('Drug(s) Prescribed.')
	if encounter.lab_test_prescription:
		subject += '<br>' + _('Test(s) Prescribed.')
	if encounter.procedure_prescription:
		subject += '<br>' + _('Procedure(s) Prescribed.')

	return subject
