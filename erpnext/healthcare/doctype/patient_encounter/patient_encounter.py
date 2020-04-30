# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr
from frappe import _

class PatientEncounter(Document):
	def on_update(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Closed')
		update_encounter_medical_record(self)

	def after_insert(self):
		insert_encounter_to_medical_record(self)

	def on_submit(self):
		update_encounter_medical_record(self)

	def on_cancel(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Open')
		delete_medical_record(self)

	def on_submit(self):
		create_therapy_plan(self)

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
	frappe.db.delete_doc_if_exists('Patient Medical Record', 'reference_name', encounter.name)

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
