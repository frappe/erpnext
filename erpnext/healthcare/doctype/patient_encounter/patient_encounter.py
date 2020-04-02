# -*- coding: utf-8 -*-
# Copyright (c) 2015, ESS LLP and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
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

	def on_cancel(self):
		if self.appointment:
			frappe.db.set_value('Patient Appointment', self.appointment, 'status', 'Open')
		delete_medical_record(self)

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
	subject = encounter.practitioner + '\n'
	if encounter.symptoms:
		subject += _('Symptoms: ') + cstr(encounter.symptoms) + '\n'
	else:
		subject +=  _('No Symptoms') + '\n'

	if encounter.diagnosis:
		subject += _('Diagnosis: ') + cstr(encounter.diagnosis) + '\n'
	else:
		subject += _('No Diagnosis') + '\n'

	if encounter.drug_prescription:
		subject += '\n' + _('Drug(s) Prescribed.')
	if encounter.lab_test_prescription:
		subject += '\n' + _('Test(s) Prescribed.')
	if encounter.procedure_prescription:
		subject += '\n' + _('Procedure(s) Prescribed.')

	return subject
